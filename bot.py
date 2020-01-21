import discord
import requests
import json
import traceback
import warnings
import time

from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext.commands import Bot

warnings.simplefilter('ignore', category=DeprecationWarning)

client = commands.Bot(command_prefix='!', help_command=None)
client.remove_command('help')


@client.event
async def on_ready():
    print('Logged in as {}'.format(client.user))
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name=f'{client.command_prefix}help | Playing '
                                                                            f'with Coroutines and Exceptions'))


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return


@client.command()
async def help(ctx):
    creator = await client.fetch_user(234491894321774592)

    help_embed = discord.Embed(description='This bot is currently under development.'
                                           '\nProduct references like prices, ratings, and links'
                                           '\nmay be in the wrong order.',
                               colour=0xe5a136)

    help_embed.add_field(name='Disclaimer', value='Price and other details may vary based on size and color',
                         inline=False)
    help_embed.add_field(name='Commands', value=f'`{client.command_prefix}help` - shows this \n'
                                                f'`{client.command_prefix}search` - search for a product\n'
                                                f'`└──` After searching a product you can\n'
                                                f' type the number of the item to get the description')
    help_embed.set_footer(text=f'Created by {creator}')

    await ctx.send(embed=help_embed)


@client.command(pass_context=True)
@commands.cooldown(1, 10, commands.BucketType.user)
async def search(ctx, *, index):
    creator = await client.fetch_user(234491894321774592)
    query = index.replace(' ', '+')

    time.sleep(0.5)
    searching_msg = await ctx.send('Searching for: `{0}`'.format(index))

    try:

        title = amazon(query)['products']
        links = amazon(query)['asin_links']
        prices = amazon(query)['prices']
        amount_of_ratings = amazon(query)['amount_of_ratings']
        ratings_context = amazon(query)['ratings_context']

        i = 0
        item_index = 0

        amazon_embed = discord.Embed()

        for _ in range(8):
            i += 1

            embedTitle = ''

            if len(title[item_index]) == 2:
                embedTitle = f'**{i}. {title[item_index][0]} {title[item_index][1]} ({ratings_context[item_index]})**'
            elif len(title[item_index]) == 1:
                embedTitle = f'**{i}. {title[item_index][0]} ({ratings_context[item_index]})**'
            else:
                embedTitle = f'**{i}. {title[item_index][0]} {title[item_index][1]} {title[item_index][2]}' \
                             f' ({ratings_context[item_index]})** '

            info = f'URL: {links[item_index]}\nPrice: {prices[item_index]}\nNumber of Ratings: {amount_of_ratings[item_index]}'

            amazon_embed.set_author(name=ctx.author, icon_url=ctx.message.author.avatar_url)
            amazon_embed.add_field(name=embedTitle, value=info, inline=False)
            amazon_embed.set_thumbnail(url=client.user.avatar_url)
            amazon_embed.set_footer(
                text=f'Made by {creator}', icon_url=creator.avatar_url)

            item_index += 1

        if await ctx.send(embed=amazon_embed):
            await searching_msg.delete()
            print('Message sent!')

    except IndexError:
        await searching_msg.delete()
        await ctx.send('No result for: `{0}`'.format(index))

    def check(author):
        def inner_check(message):
            if message.author != author:
                return False
            try:
                if int(message.content) in range(1, 8):
                    return True
            except ValueError:
                return False

        return inner_check

    msg = await client.wait_for('message', check=check(ctx.message.author), timeout=30)

    index = int(msg.content)

    title_ = (' ').join(title[index - 1])
    URL_ = links[index - 1]
    price_ = prices[index - 1]
    amount_of_ratings_ = amount_of_ratings[index - 1]
    ratings_context_ = ratings_context[index - 1]

    itemEmbed = discord.Embed(colour=0xe5a136)
    itemEmbed.set_author(name=msg.author, icon_url=msg.author.avatar_url)
    itemEmbed.add_field(name='Title:', value=f'({ratings_context_})\n{title_}')
    itemEmbed.add_field(name='URL:', value=URL_, inline=False)
    itemEmbed.add_field(name='Price:', value=price_, inline=False)
    itemEmbed.add_field(name='Number of Ratings:', value=amount_of_ratings_, inline=False)

    await ctx.send(embed=itemEmbed)


@search.error
async def search_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = 'This command is ratelimited, please try again in {:.2}s'.format(
            error.retry_after)
        await ctx.send(msg)


def amazon(URL):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/78.0.3904.108 Safari/537.36'}

    dic = {
        'products': [],
        'prices': [],
        'ratings_context': [],
        'amount_of_ratings': [],
        'asin_links': [],
    }

    page = requests.get(
        f'https://www.amazon.com/s?k={URL}&ref=nb_sb_noss_2', headers=headers)

    # Creates a BeautifulSoup object
    soup = BeautifulSoup(page.text, 'html.parser')
    soup2 = BeautifulSoup(soup.prettify(), "html.parser")

    # this grabs all product divs without a rating.
    products_without_ratings = soup2.find_all('div', {'class': 's-include-content-margin s-border-bottom'})[:8]

    for products in products_without_ratings:
        if not products.find('div', {'class': 'a-row a-size-small'}):
            products.decompose()
        if not products.find('span', {'class': 'a-offscreen'}):
            products.decompose()
        if products.find('span', {'class': 'a-size-base a-color-secondary'}):
            print(products.text.split())

    # this removes all products that are under sections like recommended
    recommended_products = soup2.find_all('div', {'class': 's-include-content-margin s-border-bottom '
                                                           's-border-top-overlap'})

    for item in recommended_products:
        item.decompose()

    for item in recommended_products:
        if item.find('div', {'data-component-type': 'sp-sponsored-result'}):
            continue


    # Get all text from this div
    amazon_list = soup2.find(class_='s-result-list s-search-results sg-row')

    # Looks for the correct title
    if amazon_list.find_all('span', {'class': 'a-size-base-plus a-color-base a-text-normal'}):
        for item in amazon_list.find_all('span', {'class': 'a-size-base-plus a-color-base a-text-normal'}):
            itemF = item.text.split()
            if itemF[0].lower() == 'free':
                continue
            dic['products'].append(itemF)
        amazon_list_items = amazon_list.find_all(
            'span', {'class': ['a-size-base-plus a-color-base a-text-normal']})[:8]

    if amazon_list.find_all('span', {'class': 'a-size-medium a-color-base a-text-normal'}):
        for item in amazon_list.find_all('span', {'class': 'a-size-medium a-color-base a-text-normal'})[:8]:
            dic['products'].append(item.text.split())

    # Get all text from these elements
    amazon_list_prices = amazon_list.find_all(
        lambda tag: tag.name == 'span' and tag.get('class') == ['a-price'])[:8]
    amazon_list_ratings = amazon_list.find_all(
        'div', {'class': 'a-row a-size-small'})[:8]
    amazon_list_links = amazon_list.find_all(
        'a', {'class': 'a-link-normal a-text-normal'})[:8]

    for price in amazon_list_prices:
        reg_price = price.find('span', {'class': 'a-offscreen'})
        if reg_price:
            dic['prices'].append(reg_price.text.strip())

    # for each rating for every amazon item
    for rating in amazon_list_ratings:
        # find the first span
        context_ratings = rating.find('span')
        dic['ratings_context'].append(context_ratings.text.strip())
        number_of_ratings = rating.find('span', {'class': 'a-size-base'})
        dic['amount_of_ratings'].append(number_of_ratings.text.strip())

    i = 0

    links = []

    for link in amazon_list_links:
        links.append(link['href'])

    for l in links:
        dp2f = l[l.find('dp%2F') + 5:].split('%' or '/')[0]
        slash_dp = l[l.find('/dp/') + 4:].split('/')[0]

        if l[l.find('/dp/') + 4:].split('/')[0]:
            dic['asin_links'].append(f'https://www.amazon.com/dp/{slash_dp}/')
        elif l[l.find('dp%2F') + 4:].split('/')[0]:
            dic['asin_links'].append(f'https://www.amazon.com/dp/{dp2f}/')
        else:
            dic['asin_links'].append('https://www.amazon.com/dp/Not_Found}/')

    return dic


token = ''
with open('config.json', 'r') as file:
    data = json.load(file)
    token = data['token']

client.run(token, bot=True)
