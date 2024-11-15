# Telegram Bot with Amazon PA-API 5 SDK

This project contains a Telegram bot written in Python that interacts with Amazon using the PA-API 5 SDK. The bot allows users to query Amazon's product catalog via Telegram, offering an easy interface for retrieving product details.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Bot Files Description](#bot-files-description)

## Prerequisites

- Python 3.7 or higher
- A Telegram bot token (You can get one by creating a bot via [BotFather](https://core.telegram.org/bots#botfather))
- Amazon PA-API 5 access key (You can get one by creating an account on [Amazon Developer](https://developer.amazon.com/))
- Install the required libraries using `pip`

## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/yourusername/telegram-amazon-bot.git
    cd telegram-amazon-bot
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Make sure you have your **Amazon API Key** and **Telegram Bot Token** ready for configuration.

## Configuration

Before running the bot, you need to configure the necessary settings in the `const.py` file:

1. **Amazon API Key**: Set your Amazon API access key in the `const.py` file:

    ```python
    AMAZON_API_KEY = 'your_amazon_api_key_here'
    ```

2. **Telegram Channel**: Set the name of your Telegram channel where the bot will send messages:

    ```python
    TELEGRAM_CHANNEL = '@your_channel_name'
    ```

## Usage

1. To start the bot, run the `bot.py` file. This will initialize the bot and begin listening for commands:

    ```bash
    python bot.py
    ```

2. The bot will start interacting with the users, responding to queries based on the commands you define in the script.

## Bot Files Description

- **bot.py**: This is the main script that starts the bot and handles user interactions. To start the bot, simply run this file.
- **const.py**: This file contains the configuration settings for the Amazon API key and the Telegram channel name. Make sure to update these before running the bot.
- **requirements.txt**: Lists the necessary Python libraries to run the bot. You can install them with `pip install -r requirements.txt`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
