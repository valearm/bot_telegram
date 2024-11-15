from sre_parse import CATEGORIES
from typing import Dict, List
import telegram
from telegram.constants import ParseMode
from amazon_api import search_items, get_item
from create_messages import create_item_html
import time
from datetime import datetime,timedelta
from itertools import chain
import random
from consts import *
import logging
import asyncio
import pytz
import os
import pickle


# Get the current working directory

import requests
from bs4 import BeautifulSoup
import re


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)

# Define conversation states
TR0, TR_ASIN, TR_LINK, TR_EDIT_START_BOT, TR_EDIT_END_BOT, TR_EDIT_INTERVAL_BOT,TR_EDIT_RATING_BOT, TR_EDIT_SALE_BOT, TR_RESTART_BOT,TR_EDIT_CATEGORY_BOT = range(10)

logging.basicConfig(level=logging.INFO)

# ********** Author: Valerio Armenante **********

categories_translation = {
    'Apparel': 'Abbigliamento',
    'Appliances': 'Elettrodomestici',
    'Automotive': 'Auto e Moto',
    'Baby': 'Prima infanzia',
    'Beauty': 'Bellezza',
    'Books': 'Libri',
    'Computers': 'Informatica',
    'DigitalMusic': 'Musica Digitale',
    'Electronics': 'Elettronica',
    'EverythingElse': 'Altro',
    'Fashion': 'Moda',
    'ForeignBooks': 'Libri in altre lingue',
    'GardenAndOutdoor': 'Giardinaggio',
    'GiftCards': 'Buoni Regalo',
    'GroceryAndGourmetFood': 'Cura della casa',
    'Handmade': 'Handmade',
    'HealthPersonalCare': 'Salute',
    'HomeAndKitchen': 'Casa e cucina',
    'Industrial': 'Industria e Scienza',
    'Jewelry': 'Gioielli',
    'KindleStore': 'Kindle Store',
    'Lighting': 'Illuminazione',
    'Luggage': 'Valigeria',
    'MobileApps': 'App e Giochi',
    'MoviesAndTV': 'Film e TV',
    'Music': 'CD e Vinili',
    'MusicalInstruments': 'Strumenti musicali',
    'OfficeProducts': 'Prodotti per ufficio',
    'PetSupplies': 'Cura per animali',
    'Shoes': 'Scarpe e borse',
    'Software': 'Software',
    'SportsAndOutdoors': 'Sport',
    'ToolsAndHomeImprovement': 'Fai da te',
    'ToysAndGames': 'Giochi e giocattoli',
    'VideoGames': 'Videogiochi',
    'Watches': 'Orologi'
}

def extract_asin_from_html(html):
    # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Attempt to find ASIN in meta tags
    meta_tags = soup.find_all('meta')
    for tag in meta_tags:
        if tag.get('name') == 'ASIN' or tag.get('data-asin'):
            return tag.get('content') or tag.get('data-asin')

    # Look for ASIN in JavaScript variables or hidden input fields
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            match = re.search(r'"ASIN":"([A-Z0-9]{10})"', script.string)
            if match:
                return match.group(1)

    # Fallback to find ASIN in canonical link
    canonical_link = soup.find('link', {'rel': 'canonical'})
    if canonical_link:
        match = re.search(r'/dp/([A-Z0-9]{10})', canonical_link.get('href', ''))
        if match:
            return match.group(1)

    # As a last resort, try to find ASIN in the page's URL
    url_match = re.search(r'/dp/([A-Z0-9]{10})', html)
    if url_match:
        return url_match.group(1)

    return None

def get_asin_from_url(url):

    logging.info(f" URL inserito:{url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, proxies={'proxy':'http://proxy.server:3128'})
        response.raise_for_status()  # Ensure the request was successful
        # logging.info(f" HTML Estratto:{response.text}")
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the <link> tag with rel="canonical" and extract the href attribute
        canonical_link = soup.find('link', {'rel': 'canonical'})
        if canonical_link:
            href = canonical_link.get('href')

            # Extract the product code (assuming it's always at the end after the last '/')
            product_code = href.split('/')[-1]

            return product_code
        else:
            print('Canonical link not found or does not contain a product code.')

        return extract_asin_from_html(soup.text)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def format_time_string(time_str):
    """
    Helper function to convert 'H' or 'HH' to 'HH:00'.
    """
    if len(time_str) == 1 or len(time_str) == 2:
        return f"{int(time_str):02d}:00"
    return time_str

def is_active() -> bool:

    italy_timezone = pytz.timezone('Europe/Rome')

    now = datetime.now(italy_timezone).time()

    logging.info(f'{5* "*"} CURRENT TIME IS : {now} {5* "*"} ')


    try:
        config_MIN_HOUR = datetime.strptime(config.MIN_HOUR, "%H:%M").time()
        config_MAX_HOUR = datetime.strptime(config.MAX_HOUR, "%H:%M").time()
    except ValueError:
        # If there's a ValueError, it might be due to incorrect formatting like "9"
        config.MIN_HOUR = format_time_string(config.MIN_HOUR)
        config.MAX_HOUR = format_time_string(config.MAX_HOUR)
        try:
            # Retry parsing after reformatting
            config_MIN_HOUR = datetime.strptime(config.MIN_HOUR, "%H:%M").time()
            config_MAX_HOUR = datetime.strptime(config.MAX_HOUR, "%H:%M").time()
        except ValueError as e:
            # Handle the case where even after reformatting, parsing fails
            print(f"Error parsing time after reformatting: {e}")
            config_MIN_HOUR = datetime.strptime("09:00" "%H:%M").time()
            config_MAX_HOUR = datetime.strptime("21:00", "%H:%M").time()

    return config_MIN_HOUR< now < config_MAX_HOUR


async def send_consecutive_messages(bot,  list_of_struct: List[str]) -> None:
    reply_markup = list_of_struct.pop()
    text = list_of_struct.pop()
    await bot.send_message(
        chat_id=CHANNEL_NAME,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )

    return list_of_struct

async def send_welcome_message(bot) -> None:
    text = """Welcome on the Telegram channel !
    """

    await bot.send_message(
        chat_id=CHANNEL_NAME,
        text=text,
        parse_mode=ParseMode.HTML,
    )

    return None


async def send_goodbye_message(bot) -> None:
    photo_caption = """ GoodBye Message Channel
"""



    photo_path = './logo.jpg'  # Update with the path to your photo

    # Send photo with initial inline keyboard
    with open(photo_path, 'rb') as photo:
        await bot.send_photo(
            chat_id=CHANNEL_NAME,
            photo=InputFile(photo),
            caption=photo_caption
        )

    return False

# run bot function
async def run_bot(bot: telegram.Bot) -> None:
    # start loop
    id_past = {}
    while True:
        try:
            items_full = []
            items_category = []
            # iterate over keywords
            for category in config.categories:

                logging.info(f'\n\n{5* "*"} RUN BOT started for category: {category} with {config.categories[category]} elements to search{5* "*"}')
                if config.categories[category] == 0:
                    logging.info(f'{5* "*"} RUN BOT skip for category: {category} {5* "*"} ')
                    continue
                items_category = []
                    # iterate over pages
                for page in range(1, 10):
                    logging.info(f'{5* "*"} RUN BOT launch search_items with page: {page}; item_count: {config.categories[category]};  {5* "*"}')
                    logging.info(f'{5* "*"} RUN BOT launch search_items min_sale = {config.MIN_SALE}; min_rate = {config.MIN_RATING}  {5* "*"} ')
                    items = search_items(category, item_page=page, min_sale = config.MIN_SALE, min_rate = config.MIN_RATING)

                    if items is None:
                        continue

                    logging.info(f'{5* "*"} RUN BOT BEFORE CHECK launch search_items found something:  {items}  {5* "*"} ')


                    items = [elem for elem in items if elem['id'] not in id_past]

                    items = [elem for elem in items if 'off' in elem]

                    items = items[:config.categories[category]]

                    logging.info(f'{5* "*"} RUN BOT AFTER CHECK launch search_items found something:  {items}  {5* "*"} ')

                    items_category.extend(items)

                    if len(items_category ) >= config.categories[category]:
                        logging.info(f'{5* "*"} RUN BOT launch search_items found limit element for category:  {category}  {5* "*"} ')
                        break

                    # api time limit for another http request is 1 second
                    await asyncio.sleep(1)


                # items_category = items_category[:config.categories[category]]
                items_full.extend(items_category)

                for item in items_full:
                    id_past[item['id']] = item
                logging.info(f'\n\n{5* "*"}  ITEMS_FULL: \n  {items_full}  {5* "*"} \n\n')



            logging.info(f'{5 * "*"} Requests Completed {5 * "*"}')

            logging.info(f'\n\n{5* "*"}  ITEMS_FULL: \n  {items_full}  {5* "*"} \n\n')

            # shuffling results times
            random.shuffle(items_full)

            # creating html message, you can find more information in create_messages.py
            res = create_item_html(items_full)

            logging.info(f'{5 * "*"} {res} {5 * "*"}')

            # while we have items in our list
            while len(res) > 0:

                # if bot is active
                if is_active():
                    try:
                        # Sending two consecutive messages
                        logging.info(f'{5 * "*"} Sto mandando i post al canale {5 * "*"}')
                        res = await send_consecutive_messages(bot, res)

                    except Exception as e:
                        logging.info(e)
                        res = res[:-2]
                        continue



                else:
                    # if bot is not active
                    logging.info(
                        f'{5 * "*"}  Bot attivo tra {config.MIN_HOUR} e le {config.MAX_HOUR} {5 * "*"}'
                    )
                    id_past = {}
                     # Your timezone
                    italy_timezone = pytz.timezone('Europe/Rome')

                    # Get the current datetime in the specified timezone
                    now = datetime.now(italy_timezone)
                    current_time = now.time()

                    logging.info(f'{5 * "*"} CURRENT TIME IS : {current_time} {5 * "*"} ')

                    # Parse the config.MIN_HOUR to a datetime object, assuming config.MIN_HOUR is a string like "09:00"
                    config_MIN_HOUR = datetime.strptime(config.MIN_HOUR, "%H:%M").time()

                    # Replace the time part of 'now' with 'config_MIN_HOUR' to get a datetime object for today
                    config_MIN_HOUR_today = now.replace(hour=config_MIN_HOUR.hour, minute=config_MIN_HOUR.minute, second=0, microsecond=0)

                    # Add 5 minutes to config_MIN_HOUR_today
                    config_MIN_HOUR_minus_5_today = config_MIN_HOUR_today + timedelta(minutes=-5)

                    logging.info(f'{5 * "*"} min_hour : {config_MIN_HOUR_today} {5 * "*"} ')

                    logging.info(f'{5 * "*"} min_hour - 5 min : {config_MIN_HOUR_minus_5_today} {5 * "*"} ')

                    # Perform the comparison
                    if config_MIN_HOUR_minus_5_today <= now <= config_MIN_HOUR_today:
                        logging.info(f'{5 * "*"} ENTERED IN THE COMPARISON  {5 * "*"} ')

                        try:
                            logging.info(f'{5 * "*"} Aggiornamento configurazioni del bot:  {5 * "*"} ')
                            with open('configuration_bot.pkl', 'rb') as file:
                                config.MIN_HOUR = pickle.load(file)
                                config.MAX_HOUR = pickle.load(file)
                                config.MIN_RATING = pickle.load(file)
                                config.MIN_SALE = pickle.load(file)
                                config.PAUSE_MINUTES = pickle.load(file)
                                config.categories = pickle.load(file)
                        except:
                            logging.warning("File Bot configuration non esiste ! ")

                        await send_welcome_message(bot)


                    # Parse the config.MIN_HOUR to a datetime object, assuming config.MIN_HOUR is a string like "09:00"
                    config_MAX_HOUR = datetime.strptime(config.MAX_HOUR, "%H:%M").time()

                    # Replace the time part of 'now' with 'config_MIN_HOUR' to get a datetime object for today
                    config_MAX_HOUR_today = now.replace(hour=config_MAX_HOUR.hour, minute=config_MAX_HOUR.minute, second=0, microsecond=0)

                    # Add 5 minutes to config_MIN_HOUR_today
                    config_MAX_HOUR_minus_5_today = config_MAX_HOUR_today + timedelta(minutes=5)

                    logging.info(f'{5 * "*"} MAX HOUR : {config_MAX_HOUR_today} {5 * "*"} ')

                    logging.info(f'{5 * "*"} MAX HOUR + 5 min : {config_MAX_HOUR_minus_5_today} {5 * "*"} ')

                    # Perform the comparison
                    if config_MAX_HOUR_today <= now <= config_MAX_HOUR_minus_5_today:
                        logging.info(f'{5 * "*"} ENTERED IN THE COMPARISON for MAX HOUR {5 * "*"} ')

                        # Write variables to a file
                        logging.info("Writing the configuration of bot on file: ")
                        with open('configuration_bot.pkl', 'wb') as file:
                            pickle.dump(config.MIN_HOUR, file)
                            pickle.dump(config.MAX_HOUR, file)
                            pickle.dump(config.MIN_RATING, file)
                            pickle.dump(config.MIN_SALE, file)
                            pickle.dump(config.PAUSE_MINUTES, file)
                            pickle.dump(config.categories, file)


                        await send_goodbye_message(bot)

                    await asyncio.sleep( 60*5  )

            # Sleep for PAUSE_MINUTES
            italy_timezone = pytz.timezone('Europe/Rome')

            # Get the current datetime in the specified timezone
            now = datetime.now(italy_timezone)
            current_time = now.time()

            # Parse the config.MIN_HOUR to a datetime object, assuming config.MIN_HOUR is a string like "09:00"
            config_MAX_HOUR = datetime.strptime(config.MAX_HOUR, "%H:%M").time()

            # Replace the time part of 'now' with 'config_MIN_HOUR' to get a datetime object for today
            config_MAX_HOUR_today = now.replace(hour=config_MAX_HOUR.hour, minute=config_MAX_HOUR.minute, second=0, microsecond=0)

            if ( config_MAX_HOUR_today -  now).total_seconds() <= (60* config.PAUSE_MINUTES):
                logging.info(f"Il tempo rimasto di attesa è : {( config_MAX_HOUR_today -  now).total_seconds() } secondi")
                await asyncio.sleep(( config_MAX_HOUR_today -  now).total_seconds() )
            else:
                logging.info(f"Il tempo rimasto di attesa è : {60 * config.PAUSE_MINUTES } secondi")
                await asyncio.sleep(60 * config.PAUSE_MINUTES)

        except Exception as e:
            logging.info(e)


# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Prepare photo and initial buttons
    current_path = os.getcwd()
    photo_path = './logo.jpg'  # Update with the path to your photo

    photo_caption = "Benvenuto sul bot Mooneis per generare tutte le offerte: "

    # Initial inline keyboard
    initial_keyboard = [
        [InlineKeyboardButton("💰 Invia Offerta !", callback_data='invia_offerta')],
        [InlineKeyboardButton("📦 Categorie ", callback_data='categorie')],
        [InlineKeyboardButton("⚙️ Impostazioni", callback_data='impostazioni')]
    ]
    reply_markup = InlineKeyboardMarkup(initial_keyboard)

    # Send photo with initial inline keyboard
    with open(photo_path, 'rb') as photo:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(photo),
            caption=photo_caption,
            reply_markup=reply_markup
        )

    return TR0

# Callback query handler for buttons
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'impostazioni':
        # New inline keyboard for "Invia Offerta"
        offer_keyboard = [
            [InlineKeyboardButton("Orario inizio", callback_data='orario_inizio'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.MIN_HOUR}", callback_data='orario_inizio')],
            [InlineKeyboardButton("Orario fine", callback_data='orario_fine'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.MAX_HOUR}", callback_data='orario_fine')],
            [InlineKeyboardButton("Intervallo", callback_data='intervallo'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.PAUSE_MINUTES}", callback_data='intervallo')],
            [InlineKeyboardButton("Rating minimo", callback_data='min_rating'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.MIN_RATING}", callback_data='min_rating')],
            [InlineKeyboardButton("Sconto minimo", callback_data='min_sale'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.MIN_SALE}", callback_data='min_sale')],
            [InlineKeyboardButton("🔙 Torna indietro", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(offer_keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return TR0  # Stay in the current state for further handling

    elif query.data == 'categorie':
        # New inline keyboard for "Invia Offerta"
        offer_keyboard = []
        for category in config.categories:
            offer_keyboard.append([InlineKeyboardButton(f"{categories_translation[category]}", callback_data=f'{category}'),  # Both buttons on the same row
                InlineKeyboardButton(f"{config.categories[category]}", callback_data=f'{category}')])

        reply_markup = InlineKeyboardMarkup(offer_keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return TR0  # Stay in the current state for further handling

    elif query.data in config.categories:
        # New inline keyboard for "Invia Offerta"
        config.update_category = query.data
        await query.edit_message_caption(caption=f"Inserisci il numero di elementi da ricercare per la categoria {categories_translation[query.data]}: ")
        logging.info(f'{5 * "*"} config.update_category = {config.update_category} e il conteggio attuale è: {config.categories[query.data]} {5 * "*"}')
        return TR_EDIT_CATEGORY_BOT  # Stay in the current state for further handling

    elif query.data == 'min_rating':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi il rating minimo di ricerca del bot qui sotto: (Inserisci un numero compreso tra 0 e 5)")
        return TR_EDIT_RATING_BOT

    elif query.data == 'min_sale':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi lo sconto minimo dei prodotti da ricercare qui sotto: (Inserisci un valore tra 0 e 100)")
        return TR_EDIT_SALE_BOT

    elif query.data == 'orario_inizio':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi L'orario di inizio del bot qui sotto: (Esempio: 09:00)")
        return TR_EDIT_START_BOT

    elif query.data == 'orario_fine':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi L'orario di fine del bot qui sotto: (Esempio: 21:00)")
        return TR_EDIT_END_BOT

    elif query.data == 'intervallo':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi L'orario di intervallo del bot qui sotto: (Numero di minuti in cui il bot effettua la ricerca ad esempio: 15)")
        return TR_EDIT_INTERVAL_BOT

    elif query.data == 'condividi_prodotto':
        return await handle_share(update, context)

    elif query.data == 'invia_offerta':
        # New inline keyboard for "Invia Offerta"
        offer_keyboard = [
            [InlineKeyboardButton("🏷️ ASIN", callback_data='asin')],
            [InlineKeyboardButton("🔗 Link", callback_data='link')],
            [InlineKeyboardButton("🔙 Torna indietro", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(offer_keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return TR0  # Stay in the current state for further handling

    elif query.data == 'back':
        # Go back to the initial inline keyboard
        return await start(update, context)

    elif query.data == 'asin':
        # Go to the ASIN input state
        await query.edit_message_caption(caption="Scrivi l'ASIN qui sotto:")
        return TR_ASIN

    elif query.data == 'link':
        # Go to the link input state
        await query.edit_message_caption(caption="Scrivi il link qui sotto:")
        return TR_LINK

    return ConversationHandler.END


async def handle_edit_rating_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rating_h = update.message.text
    if int(rating_h) > 0 and int(rating_h) <5:
        config.MIN_RATING = int(rating_h)

        # Write variables to a file
        logging.info("Writing the configuration of bot on file: ")
        with open('configuration_bot.pkl', 'wb') as file:
            pickle.dump(config.MIN_HOUR, file)
            pickle.dump(config.MAX_HOUR, file)
            pickle.dump(config.MIN_RATING, file)
            pickle.dump(config.MIN_SALE, file)
            pickle.dump(config.PAUSE_MINUTES, file)
            pickle.dump(config.categories, file)
    else:
        await update.message.reply_text(f"Inserisci un valore di rating minimo adeguato\n")
        return await start(update, context)
    await update.message.reply_text(f"Nuovo valore di rating minimo modificato in: {config.MIN_RATING}\n")
    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)

async def handle_edit_sale_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sale_h = update.message.text
    # if int(sale_h) >= 0 and int(sale_h) <=100:
    config.MIN_SALE = int(sale_h)
    logging.info("Writing the configuration of bot on file: ")
    with open('configuration_bot.pkl', 'wb') as file:
        pickle.dump(config.MIN_HOUR, file)
        pickle.dump(config.MAX_HOUR, file)
        pickle.dump(config.MIN_RATING, file)
        pickle.dump(config.MIN_SALE, file)
        pickle.dump(config.PAUSE_MINUTES, file)
        pickle.dump(config.categories, file)
    # else:
    #     await update.message.reply_text(f"Inserisci un valore di sconto minimo adeguato\n")
    #     return await start(update, context)
    await update.message.reply_text(f"Nuovo valore di sconto minimo modificato in: {config.MIN_SALE}\n")
    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)


async def handle_edit_start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_h = update.message.text
    config.MIN_HOUR = format_time_string(start_h)
    await update.message.reply_text(f"Nuovo orario di inzio impostato alle: {config.MIN_HOUR}\n")
    logging.info("Writing the configuration of bot on file: ")

    with open('configuration_bot.pkl', 'wb') as file:
        pickle.dump(config.MIN_HOUR, file)
        pickle.dump(config.MAX_HOUR, file)
        pickle.dump(config.MIN_RATING, file)
        pickle.dump(config.MIN_SALE, file)
        pickle.dump(config.PAUSE_MINUTES, file)
        pickle.dump(config.categories, file)

    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)

async def handle_edit_end_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    end_h = update.message.text
    config.MAX_HOUR = format_time_string(end_h)
    await update.message.reply_text(f"Nuovo orario di fine impostato alle: {config.MAX_HOUR}\n")
    logging.info("Writing the configuration of bot on file: ")
    with open('configuration_bot.pkl', 'wb') as file:
        pickle.dump(config.MIN_HOUR, file)
        pickle.dump(config.MAX_HOUR, file)
        pickle.dump(config.MIN_RATING, file)
        pickle.dump(config.MIN_SALE, file)
        pickle.dump(config.PAUSE_MINUTES, file)
        pickle.dump(config.categories, file)
    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)

async def handle_edit_interval_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    interval_h = update.message.text
    config.PAUSE_MINUTES = int(interval_h)
    await update.message.reply_text(f"Nuovo orario di intervallo impostato alle: {config.PAUSE_MINUTES}\n")
    logging.info("Writing the configuration of bot on file: ")
    with open('configuration_bot.pkl', 'wb') as file:
        pickle.dump(config.MIN_HOUR, file)
        pickle.dump(config.MAX_HOUR, file)
        pickle.dump(config.MIN_RATING, file)
        pickle.dump(config.MIN_SALE, file)
        pickle.dump(config.PAUSE_MINUTES, file)
        pickle.dump(config.categories, file)
    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)

async def handle_edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    n_elem = update.message.text
    config.categories[config.update_category] = int(n_elem)
    await update.message.reply_text(f"La categoria {categories_translation[config.update_category]} è impostata su {config.categories[config.update_category]}\n")

    logging.info("Writing the configuration of bot on file: ")
    with open('configuration_bot.pkl', 'wb') as file:
        pickle.dump(config.MIN_HOUR, file)
        pickle.dump(config.MAX_HOUR, file)
        pickle.dump(config.MIN_RATING, file)
        pickle.dump(config.MIN_SALE, file)
        pickle.dump(config.PAUSE_MINUTES, file)
        pickle.dump(config.categories, file)

    if config.TASK is not None:
        config.TASK.cancel()
    config.TASK = asyncio.create_task(run_bot(context.bot))
    return await start(update, context)



# Handler for state TR_ASIN (waiting for ASIN)
async def handle_asin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    asin = update.message.text
    context.user_data['asin'] = asin
    await update.message.reply_text(f"ASIN ricevuto: {asin}\nLettura dettagli del prodotto...")
    return await publish_elem(update, context)

# Handler for state TR_LINK (waiting for link)
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text
    context.user_data['link'] = link
    await update.message.reply_text(f"Link ricevuto\nLettura dettagli del prodotto...")
    return await publish_elem(update, context)

# Function to scrape Amazon for product details
async def publish_elem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    asin = context.user_data.get('asin')
    link = context.user_data.get('link')
    if link:
        # try:


            if 'dp' in link:
                logging.info("E' entrato nel dp")
                # asin = link.split('/dp/')[1].split('/')[0]
                match = re.search(r'/dp/([A-Z0-9]{10})', link)
                asin = match.group(1)

            else:
                logging.info("E' entrato nell'else del dp")
                asin = get_asin_from_url(link)
        # except:
        #     await update.message.reply_text("Errore: dati non corretti.")
        #     return await start(update, context)

    if not asin:
        await update.message.reply_text("Errore : dati non corretti.")
        return TR0

    try:
        item = get_item(asin)

        logging.info(f"item = {item}")

        res = create_item_html(item)

        # Go back to initial inline keyboard
        initial_keyboard = [
            [InlineKeyboardButton("▶️ Condividi Prodotto", callback_data='condividi_prodotto')],
            [InlineKeyboardButton("🔙 Torna indietro", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(initial_keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=res[0],
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

        context.user_data['res'] = res


    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error: {e}")
        await update.message.reply_text("Errore: dati non corretti.")
        return await start(update, context)
    except Exception as e:
        logging.error(f"General error: {e}")
        await update.message.reply_text("Errore: dati non corretti.")
        return await start(update, context)

    return TR0

async def handle_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    res = context.user_data.get('res')

    await context.bot.send_message(
        chat_id=CHANNEL_NAME,
        text=res[0],
        reply_markup=res[1],
        parse_mode=ParseMode.HTML,
    )

    return TR0

async def trigger_run_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract bot and categories from context if needed, otherwise pass directly
    bot = context.bot
    # Start run_bot (non-blocking)
    if config.TASK is None:
        config.TASK = asyncio.create_task(run_bot(bot))
    else:
        config.TASK.cancel()
        config.TASK = asyncio.create_task(run_bot(bot))
    await update.message.reply_text("Esecuzione del bot in background...")


class BotConfig:
    def __init__(self):
        self.MIN_HOUR = "07:00"
        self.MAX_HOUR = "23:00"
        self.PAUSE_MINUTES = 30
        self.MIN_SALE = 10
        self.MIN_RATING = 4
        self.TASK = None
        self.update_category = None

        self.categories = {
                'Apparel': 2,
                'Appliances': 2,
                'Automotive': 0,
                'Baby': 30,
                'Beauty': 2,
                'Books': 2,
                'Computers': 0,
                'DigitalMusic': 0,
                'Electronics': 2,
                'EverythingElse': 0,
                'Fashion': 3,
                'ForeignBooks': 0,
                'GardenAndOutdoor': 0,
                'GiftCards': 0,
                'GroceryAndGourmetFood': 3,
                'Handmade': 0,
                'HealthPersonalCare': 4,
                'HomeAndKitchen': 2,
                'Industrial': 0,
                'Jewelry': 2,
                'KindleStore': 0,
                'Lighting': 0,
                'Luggage': 0,
                'MobileApps': 2,
                'MoviesAndTV': 0,
                'Music': 0,
                'MusicalInstruments': 0,
                'OfficeProducts': 0,
                'PetSupplies': 2,
                'Shoes': 3,
                'Software': 0,
                'SportsAndOutdoors': 0,
                'ToolsAndHomeImprovement': 0,
                'ToysAndGames': 30,
                'VideoGames': 0,
                'Watches': 0
            }



if __name__ == "__main__":

    # Create a single global instance
    config = BotConfig()

    try:
        with open('configuration_bot.pkl', 'rb') as file:
            config.MIN_HOUR = pickle.load(file)
            config.MAX_HOUR = pickle.load(file)
            config.MIN_RATING = pickle.load(file)
            config.MIN_SALE = pickle.load(file)
            config.PAUSE_MINUTES = pickle.load(file)
            config.categories = pickle.load(file)
    except:
        logging.warning("File Bot configuration non esiste ! ")
    # Create the Application and pass the bot's token
    application = ApplicationBuilder().token(TOKEN).build()

    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TR0: [
                CallbackQueryHandler(button, pattern='invia_offerta'),
                CallbackQueryHandler(button, pattern='impostazioni'),
                CallbackQueryHandler(button, pattern='categorie'),
                CallbackQueryHandler(button, pattern='back'),
                CallbackQueryHandler(button, pattern='asin'),
                CallbackQueryHandler(button, pattern='link'),
                CallbackQueryHandler(button, pattern='condividi_prodotto'),
                CallbackQueryHandler(button, pattern='orario_inizio'),
                CallbackQueryHandler(button, pattern='orario_fine'),
                CallbackQueryHandler(button, pattern='intervallo'),
                CallbackQueryHandler(button, pattern='min_sale'),
                CallbackQueryHandler(button, pattern='min_rating'),

                CallbackQueryHandler(button, pattern='Apparel'),
                CallbackQueryHandler(button, pattern='Appliances'),
                CallbackQueryHandler(button, pattern='Automotive'),
                CallbackQueryHandler(button, pattern='Baby'),
                CallbackQueryHandler(button, pattern='Beauty'),
                CallbackQueryHandler(button, pattern='Books'),
                CallbackQueryHandler(button, pattern='Computers'),
                CallbackQueryHandler(button, pattern='DigitalMusic'),
                CallbackQueryHandler(button, pattern='Electronics'),
                CallbackQueryHandler(button, pattern='EverythingElse'),
                CallbackQueryHandler(button, pattern='Fashion'),
                CallbackQueryHandler(button, pattern='ForeignBooks'),
                CallbackQueryHandler(button, pattern='GardenAndOutdoor'),
                CallbackQueryHandler(button, pattern='GiftCards'),
                CallbackQueryHandler(button, pattern='GroceryAndGourmetFood'),
                CallbackQueryHandler(button, pattern='Handmade'),
                CallbackQueryHandler(button, pattern='HealthPersonalCare'),
                CallbackQueryHandler(button, pattern='HomeAndKitchen'),
                CallbackQueryHandler(button, pattern='Industrial'),
                CallbackQueryHandler(button, pattern='Jewelry'),
                CallbackQueryHandler(button, pattern='KindleStore'),
                CallbackQueryHandler(button, pattern='Lighting'),
                CallbackQueryHandler(button, pattern='Luggage'),
                CallbackQueryHandler(button, pattern='MobileApps'),
                CallbackQueryHandler(button, pattern='MoviesAndTV'),
                CallbackQueryHandler(button, pattern='Music'),
                CallbackQueryHandler(button, pattern='MusicalInstruments'),
                CallbackQueryHandler(button, pattern='OfficeProducts'),
                CallbackQueryHandler(button, pattern='PetSupplies'),
                CallbackQueryHandler(button, pattern='Shoes'),
                CallbackQueryHandler(button, pattern='Software'),
                CallbackQueryHandler(button, pattern='SportsAndOutdoors'),
                CallbackQueryHandler(button, pattern='ToolsAndHomeImprovement'),
                CallbackQueryHandler(button, pattern='ToysAndGames'),
                CallbackQueryHandler(button, pattern='VideoGames'),
                CallbackQueryHandler(button, pattern='Watches'),

                MessageHandler(filters.TEXT & ~filters.COMMAND, start)
            ],
            TR_ASIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_asin)],
            TR_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
            TR_EDIT_START_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_start_bot)],
            TR_EDIT_END_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_end_bot)],
            TR_EDIT_INTERVAL_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_interval_bot)],
            TR_EDIT_RATING_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_rating_bot)],
            TR_EDIT_CATEGORY_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_category)],
            TR_EDIT_SALE_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_sale_bot)],
            TR_RESTART_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, trigger_run_bot)]
        },
        fallbacks=[CommandHandler('start', start)],
    )


    # Add handlers to the application
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('runbot', trigger_run_bot))  # Add a command to trigger run_bot

    # for category in config.categories:

    #     handler = CallbackQueryHandler(button, pattern=f'{category}')
    #     application.add_handler(handler)

    # Run the bot
    application.run_polling()


