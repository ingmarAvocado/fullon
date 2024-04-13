#!/usr/bin/python3
"""
This is a command line tool for managing persea
"""
from inspect import Attribute
from typing import Any, Tuple, Dict, Optional
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from tabulate import tabulate
from libs import log
from libs.database import Database
from run.user_manager import UserManager
from clint.textui import colored
from run.simul_manager import SimulManager

logger = log.fullon_logger(__name__)

COMPRESSIONS = {'ticks': [1],
                'minutes': [1, 2, 3, 4, 5, 10, 12, 15, 20, 30, 60, 120, 240, 480, 720],
                'days': [1, 2, 3, 4, 5, 6, 7],
                'weeks': [1, 2, 3, 4],
                'months': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}


class Prompts():
    """
    Class for managing prompts and interactions with the user.
    """

    USER: str = 'admin@fullon'
    UID: Any = ''
    BOT = ('', 'No bot set', '')
    STR_PARAMS = {}
    FEEDS = {}
    SIMUL_PARAMS = {}

    def __init__(self):
        user = UserManager()
        self.UID = user.get_user_id(mail='admin@fullon')
        self.simul = SimulManager()

    def set_user(self):
        """
        Set the user based on user input.
        """
        with Database() as dbase:
            users = dbase.get_user_list(full=True)

        numusers = {}

        for n, user in enumerate(users):
            print(f"{n+1}: {user[1]}")
            numusers[n+1] = (user[0], user[1])

        while True:
            print("User List:")
            user_table = [[num, user[1]] for num, user in numusers.items()]
            print(tabulate(user_table, headers=["Number", "User"], tablefmt="fancy_grid"))

            try:
                session = PromptSession()
                user_input = session.prompt("Type user number: ")
                num = int(user_input)

                if num in numusers:
                    self.USER = numusers[num][1]
                    self.UID = numusers[num][0]
                    print(f"User {self.USER} has been set")
                    break
                else:
                    print("Wrong key, number not in the database.")
            except ValueError:
                print("Please enter a valid user number.")

    def _get_bot_dict(self) -> Dict[int, Tuple[str, str, str]]:
        """
        Creates a dictionary with the bots from a user.

        :return: A dictionary containing the bot information.
        """
        with Database() as dbase:
            bots = dbase.get_bot_list(uid=self.UID)

        if not bots:
            print("No bots for this user")
            return {}

        numbots = {}
        for n, bot in enumerate(bots, start=1):
            numbots[n] = (bot.bot_id, bot.name)
        return numbots

    def _pre_set_bot(self):
        """
        pre sets all bot simulation parameters
        """
        # first str_params
        self.STR_PARAMS = self._get_str_params()
        # now feeds
        self.FEEDS = self._get_feeds()
        #  now simul params
        self.SIMUL_PARAMS = {"periods": {"bars": 200},
                             "warm_up": {"bars": 50},
                             "xls": {"save xls": False},
                             "verbose": {"print trades": False},
                             "visual": {"graph": 0},
                             "event": {"event based simul": True}}

    def set_bot(self):
        """
        Set the bot based on user input.
        """
        numbots = self._get_bot_dict()

        while True:
            print("Bot List:")
            bot_table = [[num, bot[1]] for num, bot in numbots.items()]
            print(tabulate(bot_table, headers=["Number", "Bot"], tablefmt="fancy_grid"))

            try:
                session = PromptSession()
                user_input = session.prompt("Which bot number: ")
                num = int(user_input)

                if num in numbots:
                    self.BOT = numbots[num]
                    print(f"Bot {self.BOT[1]} has been set")
                    self._pre_set_bot()
                    break
                else:
                    print("Wrong key, number not in the database.")
            except ValueError:
                print("Please enter a valid bot number.")

    def _get_str_params(self) -> list:
        """
        Set the strategy parameters for the bot.

        :return: A list of dictionaries, each containing strategy parameters including both base and additional ones.
        """
        bot_id = self.BOT[0]
        with Database() as dbase:
            # Fetch both sets of parameters in a single database connection
            strats = dbase.get_str_params(bot_id=bot_id)
            base_params = dbase.get_base_str_params(bot_id=bot_id)
        # Assuming both base_params and strats return a list of dictionaries, where each dict contains 'str_id' and parameters
        return base_params

    def set_str_params(self):
        """
        Set the strategy parameters based on user input.
        """
        if not self.BOT[0]:
            print(colored.red("\nNo bot assigned yet, please pick one with comand 'bots'\n"))
            return
        param_names = list(self.STR_PARAMS.keys())
        completer = WordCompleter(param_names)

        session = PromptSession(completer=completer, complete_style=CompleteStyle.MULTI_COLUMN)

        while True:
            table = tabulate(self.STR_PARAMS.items(), headers=["Parameter", "Value"], tablefmt="fancy_grid")
            print(table)

            try:
                pre_prompt = HTML(f'<ansigreen>Enter a parameter name to modify (CTRL-D to go back): </ansigreen>')
                user_input = session.prompt(pre_prompt)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if user_input in param_names:
                new_value = session.prompt(f"Enter a new value for {user_input}: ")
                self.STR_PARAMS[user_input] = new_value
            else:
                print("Invalid parameter name. Please try again.")

        print("Updated parameter values:")
        table = tabulate(self.STR_PARAMS.items(), headers=["Parameter", "Value"], tablefmt="fancy_grid")
        print(table)

    def _get_feeds(self) -> dict:
        """
        Set the feed dictionary for the bot.

        :return: A list of modified feeds.
        """
        ret_feeds = {}
        with Database() as dbase:
            feeds = dbase.get_bot_feeds(bot_id=self.BOT[0])
        for num, feed in enumerate(feeds):
            ret_feeds[num] = {'Compression': feed.compression, 'Period': feed.period}
        return ret_feeds

    def set_feeds(self):
        """
        Set the feeds based on user input.
        """
        if not self.BOT[0]:
            print(colored.red("\nNo bot assigned yet, please pick one with command 'bots'\n"))
            return
        param_names = list(self.FEEDS.keys())
        session = PromptSession(complete_style=CompleteStyle.MULTI_COLUMN)
        periods = ["Ticks", "Minutes", "Days", "Weeks", "Months"]
        period_options = WordCompleter(periods)
        field_options = WordCompleter(['Period', 'Compression'], ignore_case=True)

        while True:
            feed_table = [[feed_num, feed['Period'], feed['Compression']] for feed_num, feed in self.FEEDS.items()]
            headers = ["Feed Num", "Period", "Compression"]

            print(tabulate(feed_table, headers=headers, tablefmt="fancy_grid"))

            try:
                pre_prompt = HTML('<ansigreen>Enter a feed number to modify period and compression (CTRL-D to go back): </ansigreen>')
                user_input = session.prompt(pre_prompt)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if int(user_input) in param_names:
                strperiod = ', '.join(periods)
                new_period = session.prompt(f"Enter a new period value ({strperiod}): ", completer=period_options)
                if new_period in periods:
                    self.FEEDS[int(user_input)]['Period'] = new_period
                    new_compression = session.prompt("Enter a new compression value: ")
                    if int(new_compression) in COMPRESSIONS[new_period.lower()]:
                        self.FEEDS[int(user_input)]['Compression'] = int(new_compression)
                    else:
                        str_compressions = COMPRESSIONS[new_period.lower()]
                        print(f"Invalid compression ({new_compression}) number for {new_period} valid values are: ({str_compressions})")
                else:
                    print(f"Invalid period pick one of the following ({strperiod})")

            else:
                print("Invalid feed number. Please try again.")

        print("Updated feed values:")
        feed_table = [[feed_num, feed['Period'], feed['Compression']] for feed_num, feed in self.FEEDS.items()]
        print(tabulate(feed_table, headers=headers, tablefmt="fancy_grid"))

    def set_simul_params(self):
        """
        Set the simulation parameters based on user input.
        """
        if not self.BOT[0]:
            print(colored.red("\nNo bot assigned yet, please pick one with command 'bots'\n"))
            return

        param_names = list(self.SIMUL_PARAMS.keys())
        session = PromptSession(complete_style=CompleteStyle.MULTI_COLUMN)
        param_options = WordCompleter(param_names)

        while True:
            simul_params_table = [[param_name, list(param.keys())[0], list(param.values())[0]] for param_name, param in self.SIMUL_PARAMS.items()]
            headers = ["Param Name", "Description", "Param Value"]

            print(tabulate(simul_params_table, headers=headers, tablefmt="fancy_grid"))

            try:
                pre_prompt = HTML('<ansigreen>Enter a parameter name to modify its value (CTRL-D to go back): </ansigreen>')
                user_input = session.prompt(pre_prompt, completer=param_options)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if user_input in param_names:
                new_value = session.prompt(f"Enter a new value for {user_input}: ")
                if isinstance(list(self.SIMUL_PARAMS[user_input].values())[0], bool):
                    new_value = new_value.lower() in ('true', '1')
                elif isinstance(list(self.SIMUL_PARAMS[user_input].values())[0], int):
                    new_value = int(new_value)
                self.SIMUL_PARAMS[user_input][list(self.SIMUL_PARAMS[user_input].keys())[0]] = new_value
            else:
                print("Invalid parameter name. Please try again.")

        print("Updated simulation parameters:")
        simul_params_table = [[param_name, list(param.keys())[0], list(param.values())[0]] for param_name, param in self.SIMUL_PARAMS.items()]
        print(tabulate(simul_params_table, headers=headers, tablefmt="fancy_grid"))

    def save_simul(self):
        """
        Saves simulation to the database
        """
        # first we build a python dict
        try:
            if self.UID and self.BOT and self.STR_PARAMS and self.FEEDS and self.SIMUL_PARAMS:
                save = {'uid': self.UID,
                        'bot': self.BOT,
                        'str_params': self.STR_PARAMS,
                        'feeds': self.FEEDS,
                        'simul_params': self.SIMUL_PARAMS}
                name = input("Simulation name: ")
                with Database() as dbase:
                    dbase.save_simulation(bot_id=self.BOT[0], name=self.BOT[1]+f": ({name})", payload=save)
                print(colored.green("\nSimulation parameters have been saved!"))
        except AttributeError:
            print("Make sure you have picked bot, feeds, strats, params")

    @staticmethod
    def _load_simul_prompts():
        limit_prompt = "Enter a limit for the number of simulations to load (leave empty for default): "
        starts_with_prompt = "Enter a starting string to filter simulations by name (leave empty for no filter): "
        session = PromptSession()
        try:
            limit_input = session.prompt(limit_prompt)
            starts_with_input = session.prompt(starts_with_prompt)
        except KeyboardInterrupt:
            return (20, '')
        except EOFError:
            return (20, '')
        limit = int(limit_input) if limit_input.isdigit() else 20
        starts_with = starts_with_input if starts_with_input else ''
        return (limit, starts_with)

    def load_simul(self):
        """
        Load simulations from the database, presents a menu for the user to choose from, 
        and then loads the selected simulation parameters into the appropriate instance variables.

        Raises:
            psycopg2.DatabaseError: If an error occurs while retrieving simulations from the database.
        """
        session = PromptSession(complete_style=CompleteStyle.MULTI_COLUMN)
        page = 0
        limit = 20
        starts_with = ''

        # Convert user input to appropriate types (or use default values)
        while True:
            with Database() as dbase:
                rows = dbase.load_simulations_catalog(limit, starts_with, page*limit)

            if not rows:
                print("No simulations found in the database.")
                return


            # Print simulations table for the user to pick a simulation
            simulation_table = [[row[0], row[1]] for row in rows]  # Use indexing to access values
            headers = ["Num", "Simul Name"]
            simulation_indices = [str(row[0]) for row in rows]
            index_options = WordCompleter(simulation_indices, ignore_case=True)

            while True:
                try:
                    print(tabulate(simulation_table, headers=headers, tablefmt="fancy_grid"))
                    print("Type n for next page, p for previous page, z to search simulations")
                    pre_prompt = HTML("<ansigreen>Enter a simulation number to load CTRL-D to go back: </ansigreen>")
                    user_input = session.prompt(pre_prompt)
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    return

                if user_input.lower() == 'n':
                    page += 1
                    break
                elif user_input.lower() == 'p' and page > 0:
                    page -= 1
                    break
                elif user_input.lower() == 'z':
                    limit, starts_with = self._load_simul_prompts()

                if user_input in simulation_indices:
                    user_input = int(user_input)
                    with Database() as dbase:
                        params = dbase.load_simulation(num=user_input)
                    if params:
                        name = params[1]
                        params = params[0]
                        params_table = [(k, v) for k, v in params.get('str_params').items()]
                        print(tabulate(params_table, headers=['Parameter', 'Value'], tablefmt="fancy_grid"))
                        try:
                            confirmation = session.prompt(f"Are you sure u want to load simul {name} (y/n) ")
                        except KeyboardInterrupt:
                            continue
                        except EOFError:
                            return
                        if confirmation == 'y':
                            self.UID = params.get('uid')
                            self.BOT = params.get('bot')
                            self.STR_PARAMS = params.get('str_params')
                            self.FEEDS = params.get('feeds')
                            self.SIMUL_PARAMS = params.get('simul_params')
                            return
                else:
                    print("Invalid simulation number. Please try again.")

    def run_simul(self):
        """
        will execute the simulation
        """
        bot = {'bot_id': self.BOT[0]}
        for key, param in self.SIMUL_PARAMS.items():
            values = list(param.values())
            bot[key] = values[0]
        event = bool(bot['event'])
        del bot['event']
        feeds = {}
        for num, feed in self.FEEDS.items():
            match feed['Period'].lower():
                case 'minutes':
                    feeds[num] = {'compression': feed['Compression']}
                case 'days':
                    minutes = int(feed['Compression']) * 60 * 24
                    feeds[num] = {'compression': minutes}
                case 'weeks':
                    minutes = int(feed['Compression']) * 60 * 24*7
                    feeds[num] = {'compression': minutes}
        params = {}
        for key, value in self.STR_PARAMS.items():
            if value:
                params[key] = str(value)
        self.simul.bot_simul(bot=bot, event_based=event, feeds=feeds, params=params)
