-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 1.1.3
-- PostgreSQL version: 16.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: fullon | type: DATABASE --
-- DROP DATABASE IF EXISTS fullon;
CREATE DATABASE fullon;
-- ddl-end --


-- object: public.cat_exchanges | type: TABLE --
-- DROP TABLE IF EXISTS public.cat_exchanges CASCADE;
CREATE TABLE public.cat_exchanges (
	cat_ex_id serial NOT NULL,
	name varchar(30) NOT NULL,
	ohlcv_view text,
	CONSTRAINT cat_exchange_pk PRIMARY KEY (cat_ex_id),
	CONSTRAINT unique_ex UNIQUE (name)
);
-- ddl-end --
ALTER TABLE public.cat_exchanges OWNER TO postgres;
-- ddl-end --

-- object: public.exchanges | type: TABLE --
-- DROP TABLE IF EXISTS public.exchanges CASCADE;
CREATE TABLE public.exchanges (
	ex_id serial NOT NULL,
	uid integer NOT NULL,
	cat_ex_id integer NOT NULL,
	name varchar(50) NOT NULL,
	test bool NOT NULL DEFAULT false,
	active bool NOT NULL DEFAULT True,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	CONSTRAINT exchange_pk PRIMARY KEY (ex_id),
	CONSTRAINT unique_user_exchange UNIQUE (uid,cat_ex_id,name)
);
-- ddl-end --
ALTER TABLE public.exchanges OWNER TO postgres;
-- ddl-end --

-- object: public.users | type: TABLE --
-- DROP TABLE IF EXISTS public.users CASCADE;
CREATE TABLE public.users (
	uid serial NOT NULL,
	mail varchar(80) NOT NULL,
	password char(64) NOT NULL,
	f2a varchar(16) NOT NULL,
	role varchar(10) NOT NULL,
	name varchar(50) NOT NULL,
	lastname varchar(50) NOT NULL,
	phone varchar(12) NOT NULL,
	id_num varchar(15) NOT NULL,
	note text,
	manager integer,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	active bool NOT NULL DEFAULT True,
	CONSTRAINT users_pk PRIMARY KEY (uid),
	CONSTRAINT unique_mail UNIQUE (mail)
);
-- ddl-end --
ALTER TABLE public.users OWNER TO postgres;
-- ddl-end --

-- object: public.cat_strategies | type: TABLE --
-- DROP TABLE IF EXISTS public.cat_strategies CASCADE;
CREATE TABLE public.cat_strategies (
	cat_str_id serial NOT NULL,
	name varchar(50) NOT NULL,
	take_profit float,
	stop_loss float,
	trailing_stop float,
	timeout float,
	pre_load_bars smallint NOT NULL DEFAULT 200,
	feeds smallint NOT NULL DEFAULT 2,
	pairs bool DEFAULT False,
	CONSTRAINT cat_strategies_pk PRIMARY KEY (cat_str_id),
	CONSTRAINT "unique name" UNIQUE (name)
);
-- ddl-end --
ALTER TABLE public.cat_strategies OWNER TO postgres;
-- ddl-end --

-- object: public.strategies | type: TABLE --
-- DROP TABLE IF EXISTS public.strategies CASCADE;
CREATE TABLE public.strategies (
	str_id serial NOT NULL,
	bot_id integer,
	cat_str_id integer NOT NULL,
	take_profit float,
	stop_loss float,
	trailing_stop float,
	timeout float,
	leverage float NOT NULL DEFAULT 1,
	size_pct float,
	size float,
	size_currency varchar(5),
	pre_load_bars smallint,
	feeds smallint DEFAULT 2,
	pairs bool DEFAULT False,
	CONSTRAINT strategies_pk PRIMARY KEY (str_id)
);
-- ddl-end --
ALTER TABLE public.strategies OWNER TO postgres;
-- ddl-end --

-- object: public.bots | type: TABLE --
-- DROP TABLE IF EXISTS public.bots CASCADE;
CREATE TABLE public.bots (
	bot_id serial NOT NULL,
	uid integer NOT NULL,
	name varchar(50) NOT NULL,
	dry_run bool DEFAULT False,
	active bool NOT NULL DEFAULT False,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	CONSTRAINT bot_pk PRIMARY KEY (bot_id),
	CONSTRAINT bot_id_name_unique UNIQUE (bot_id,name)
);
-- ddl-end --
ALTER TABLE public.bots OWNER TO postgres;
-- ddl-end --

-- object: public.symbols | type: TABLE --
-- DROP TABLE IF EXISTS public.symbols CASCADE;
CREATE TABLE public.symbols (
	symbol_id serial NOT NULL,
	symbol varchar(20) NOT NULL,
	cat_ex_id integer NOT NULL,
	updateframe varchar(2) NOT NULL DEFAULT '1h',
	backtest smallint NOT NULL DEFAULT 30,
	decimals smallint NOT NULL DEFAULT 8,
	base varchar(6) NOT NULL,
	ex_base varchar(6),
	futures bool NOT NULL DEFAULT false,
	only_ticker bool NOT NULL DEFAULT False,
	CONSTRAINT symbol_pk PRIMARY KEY (symbol_id),
	CONSTRAINT "symbol_Exchange" UNIQUE (symbol,cat_ex_id)
);
-- ddl-end --
ALTER TABLE public.symbols OWNER TO postgres;
-- ddl-end --

-- object: public.cat_exchanges_params | type: TABLE --
-- DROP TABLE IF EXISTS public.cat_exchanges_params CASCADE;
CREATE TABLE public.cat_exchanges_params (
	cat_ex_id integer NOT NULL,
	name varchar(20) NOT NULL,
	value varchar(20) NOT NULL,
	CONSTRAINT unique_param_symbol UNIQUE (cat_ex_id,name)
);
-- ddl-end --
ALTER TABLE public.cat_exchanges_params OWNER TO postgres;
-- ddl-end --

-- object: public.cat_strategies_params | type: TABLE --
-- DROP TABLE IF EXISTS public.cat_strategies_params CASCADE;
CREATE TABLE public.cat_strategies_params (
	cat_str_id integer NOT NULL,
	name text NOT NULL,
	value text NOT NULL,
	CONSTRAINT unique_param_symbol1 UNIQUE (cat_str_id,name)
);
-- ddl-end --
ALTER TABLE public.cat_strategies_params OWNER TO postgres;
-- ddl-end --

-- object: public.strategies_params | type: TABLE --
-- DROP TABLE IF EXISTS public.strategies_params CASCADE;
CREATE TABLE public.strategies_params (
	str_id integer NOT NULL,
	name text NOT NULL,
	value text NOT NULL,
	CONSTRAINT unique_param_symbol2 UNIQUE (str_id,name)
);
-- ddl-end --
ALTER TABLE public.strategies_params OWNER TO postgres;
-- ddl-end --

-- object: public.bot_log | type: TABLE --
-- DROP TABLE IF EXISTS public.bot_log CASCADE;
CREATE TABLE public.bot_log (
	bot_id integer NOT NULL,
	feed_num smallint NOT NULL,
	ex_id integer NOT NULL,
	symbol text NOT NULL,
	"position" numeric NOT NULL,
	message text NOT NULL,
	"timestamp" timestamp with time zone NOT NULL DEFAULT current_timestamp

);
-- ddl-end --
ALTER TABLE public.bot_log OWNER TO postgres;
-- ddl-end --

-- object: public.orders | type: TABLE --
-- DROP TABLE IF EXISTS public.orders CASCADE;
CREATE TABLE public.orders (
	order_id serial NOT NULL,
	bot_id integer NOT NULL,
	uid integer NOT NULL,
	ex_id integer NOT NULL,
	ex_order_id varchar(64),
	cat_ex_id integer NOT NULL,
	exchange varchar(50) NOT NULL,
	symbol varchar(20) NOT NULL,
	order_type varchar(15) NOT NULL,
	side varchar(4) NOT NULL,
	volume double precision NOT NULL,
	final_volume double precision,
	price double precision,
	plimit double precision,
	tick double precision,
	futures bool NOT NULL DEFAULT false,
	status varchar(20) NOT NULL,
	command varchar(64),
	reason varchar(35) NOT NULL,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	CONSTRAINT orders_pk PRIMARY KEY (order_id)
);
-- ddl-end --
ALTER TABLE public.orders OWNER TO postgres;
-- ddl-end --

-- object: uid_ex_id | type: INDEX --
-- DROP INDEX IF EXISTS public.uid_ex_id CASCADE;
CREATE INDEX uid_ex_id ON public.orders
USING btree
(
	uid,
	ex_id,
	status
);
-- ddl-end --

-- object: bot_symbol_index | type: INDEX --
-- DROP INDEX IF EXISTS public.bot_symbol_index CASCADE;
CREATE INDEX bot_symbol_index ON public.orders
USING btree
(
	bot_id,
	status,
	symbol
);
-- ddl-end --

-- object: public.trades | type: TABLE --
-- DROP TABLE IF EXISTS public.trades CASCADE;
CREATE TABLE public.trades (
	trade_id serial NOT NULL,
	ex_trade_id varchar(64) NOT NULL,
	ex_order_id varchar(64) NOT NULL,
	uid integer NOT NULL,
	ex_id integer NOT NULL,
	symbol varchar(20) NOT NULL,
	order_type varchar(15) NOT NULL,
	side varchar(4) NOT NULL,
	volume double precision NOT NULL,
	price double precision NOT NULL,
	cost double precision NOT NULL,
	fee double precision NOT NULL,
	cur_volume double precision,
	cur_avg_price double precision,
	cur_avg_cost double precision,
	cur_fee double precision,
	roi double precision,
	roi_pct double precision,
	total_fee double precision,
	leverage float,
	"time" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	CONSTRAINT trades_pk PRIMARY KEY (trade_id),
	CONSTRAINT unique_order_id UNIQUE (ex_trade_id,ex_order_id)
);
-- ddl-end --
ALTER TABLE public.trades OWNER TO postgres;
-- ddl-end --

-- object: "one oid" | type: INDEX --
-- DROP INDEX IF EXISTS public."one oid" CASCADE;
CREATE UNIQUE INDEX "one oid" ON public.trades
USING btree
(
	trade_id
);
-- ddl-end --

-- object: uid_ex_id_trades | type: INDEX --
-- DROP INDEX IF EXISTS public.uid_ex_id_trades CASCADE;
CREATE INDEX uid_ex_id_trades ON public.trades
USING btree
(
	uid,
	ex_id
);
-- ddl-end --

-- object: public.bot_exchanges | type: TABLE --
-- DROP TABLE IF EXISTS public.bot_exchanges CASCADE;
CREATE TABLE public.bot_exchanges (
	bot_id integer NOT NULL,
	ex_id integer NOT NULL,
	CONSTRAINT unique_record UNIQUE (bot_id,ex_id)
);
-- ddl-end --
ALTER TABLE public.bot_exchanges OWNER TO postgres;
-- ddl-end --

-- object: public.exchange_history | type: TABLE --
-- DROP TABLE IF EXISTS public.exchange_history CASCADE;
CREATE TABLE public.exchange_history (
	ex_id integer NOT NULL,
	user_id integer NOT NULL,
	currency varchar(15) NOT NULL,
	balance double precision NOT NULL,
	comment text,
	"timestamp" timestamp NOT NULL

);
-- ddl-end --
ALTER TABLE public.exchange_history OWNER TO postgres;
-- ddl-end --

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- object: public.dry_trades | type: TABLE --
-- DROP TABLE IF EXISTS public.dry_trades CASCADE;
CREATE TABLE public.dry_trades (
	trade_id serial NOT NULL,
	bot_id integer NOT NULL,
	uid integer NOT NULL,
	ex_id integer NOT NULL,
	symbol varchar(20) NOT NULL,
	side varchar(4) NOT NULL,
	volume double precision NOT NULL,
	price double precision NOT NULL,
	cost double precision NOT NULL,
	fee double precision NOT NULL,
	roi double precision,
	roi_pct double precision,
	reason varchar(35),
	closingtrade bool NOT NULL DEFAULT False,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	CONSTRAINT trades_simul_pk PRIMARY KEY (trade_id)
);
-- ddl-end --
ALTER TABLE public.dry_trades OWNER TO postgres;
-- ddl-end --

-- object: "one oid_cp" | type: INDEX --
-- DROP INDEX IF EXISTS public."one oid_cp" CASCADE;
CREATE UNIQUE INDEX "one oid_cp" ON public.dry_trades
USING btree
(
	trade_id
);
-- ddl-end --

-- object: uid_ex_id_trades_cp | type: INDEX --
-- DROP INDEX IF EXISTS public.uid_ex_id_trades_cp CASCADE;
CREATE INDEX uid_ex_id_trades_cp ON public.dry_trades
USING btree
(
	uid,
	ex_id
);
-- ddl-end --

CREATE OR REPLACE FUNCTION public.first_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $1;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE public.FIRST (
        sfunc    = public.first_agg,
        basetype = anyelement,
        stype    = anyelement
);
 
-- Create a function that always returns the last non-NULL item
CREATE OR REPLACE FUNCTION public.last_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $2;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE public.LAST (
        sfunc    = public.last_agg,
        basetype = anyelement,
        stype    = anyelement
);
-- object: public.feeds | type: TABLE --
-- DROP TABLE IF EXISTS public.feeds CASCADE;
CREATE TABLE public.feeds (
	feed_id serial NOT NULL,
	str_id integer NOT NULL,
	symbol_id integer NOT NULL,
	period varchar(10) NOT NULL,
	compression smallint NOT NULL,
	"order" smallint NOT NULL,
	CONSTRAINT feed_pk PRIMARY KEY (feed_id)
);
-- ddl-end --
ALTER TABLE public.feeds OWNER TO postgres;
-- ddl-end --

-- object: public.simulations | type: TABLE --
-- DROP TABLE IF EXISTS public.simulations CASCADE;
CREATE TABLE public.simulations (
	num serial NOT NULL,
	bot_id integer NOT NULL,
	name varchar(35) NOT NULL,
	json json,
	CONSTRAINT bot_name UNIQUE (bot_id,name),
	CONSTRAINT serial_primary PRIMARY KEY (num)
);
-- ddl-end --
ALTER TABLE public.simulations OWNER TO postgres;
-- ddl-end --

-- object: user_id | type: CONSTRAINT --
-- ALTER TABLE public.exchanges DROP CONSTRAINT IF EXISTS user_id CASCADE;
ALTER TABLE public.exchanges ADD CONSTRAINT user_id FOREIGN KEY (uid)
REFERENCES public.users (uid) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: exchange_cat_exchange | type: CONSTRAINT --
-- ALTER TABLE public.exchanges DROP CONSTRAINT IF EXISTS exchange_cat_exchange CASCADE;
ALTER TABLE public.exchanges ADD CONSTRAINT exchange_cat_exchange FOREIGN KEY (cat_ex_id)
REFERENCES public.cat_exchanges (cat_ex_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE RESTRICT;
-- ddl-end --

-- object: client_manager | type: CONSTRAINT --
-- ALTER TABLE public.users DROP CONSTRAINT IF EXISTS client_manager CASCADE;
ALTER TABLE public.users ADD CONSTRAINT client_manager FOREIGN KEY (manager)
REFERENCES public.users (uid) MATCH FULL
ON DELETE RESTRICT ON UPDATE RESTRICT;
-- ddl-end --

-- object: cat_str_id | type: CONSTRAINT --
-- ALTER TABLE public.strategies DROP CONSTRAINT IF EXISTS cat_str_id CASCADE;
ALTER TABLE public.strategies ADD CONSTRAINT cat_str_id FOREIGN KEY (cat_str_id)
REFERENCES public.cat_strategies (cat_str_id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: many_str_one_bot | type: CONSTRAINT --
-- ALTER TABLE public.strategies DROP CONSTRAINT IF EXISTS many_str_one_bot CASCADE;
ALTER TABLE public.strategies ADD CONSTRAINT many_str_one_bot FOREIGN KEY (bot_id)
REFERENCES public.bots (bot_id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: bot_user | type: CONSTRAINT --
-- ALTER TABLE public.bots DROP CONSTRAINT IF EXISTS bot_user CASCADE;
ALTER TABLE public.bots ADD CONSTRAINT bot_user FOREIGN KEY (uid)
REFERENCES public.users (uid) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: cat_ex_id | type: CONSTRAINT --
-- ALTER TABLE public.symbols DROP CONSTRAINT IF EXISTS cat_ex_id CASCADE;
ALTER TABLE public.symbols ADD CONSTRAINT cat_ex_id FOREIGN KEY (cat_ex_id)
REFERENCES public.cat_exchanges (cat_ex_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE RESTRICT;
-- ddl-end --

-- object: cat_ex_id | type: CONSTRAINT --
-- ALTER TABLE public.cat_exchanges_params DROP CONSTRAINT IF EXISTS cat_ex_id CASCADE;
ALTER TABLE public.cat_exchanges_params ADD CONSTRAINT cat_ex_id FOREIGN KEY (cat_ex_id)
REFERENCES public.cat_exchanges (cat_ex_id) MATCH FULL
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: cat_str_id | type: CONSTRAINT --
-- ALTER TABLE public.cat_strategies_params DROP CONSTRAINT IF EXISTS cat_str_id CASCADE;
ALTER TABLE public.cat_strategies_params ADD CONSTRAINT cat_str_id FOREIGN KEY (cat_str_id)
REFERENCES public.cat_strategies (cat_str_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: cat_id | type: CONSTRAINT --
-- ALTER TABLE public.strategies_params DROP CONSTRAINT IF EXISTS cat_id CASCADE;
ALTER TABLE public.strategies_params ADD CONSTRAINT cat_id FOREIGN KEY (str_id)
REFERENCES public.strategies (str_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: bot_uid | type: CONSTRAINT --
-- ALTER TABLE public.bot_log DROP CONSTRAINT IF EXISTS bot_uid CASCADE;
ALTER TABLE public.bot_log ADD CONSTRAINT bot_uid FOREIGN KEY (bot_id)
REFERENCES public.bots (bot_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: ex_to_bots | type: CONSTRAINT --
-- ALTER TABLE public.bot_exchanges DROP CONSTRAINT IF EXISTS ex_to_bots CASCADE;
ALTER TABLE public.bot_exchanges ADD CONSTRAINT ex_to_bots FOREIGN KEY (bot_id)
REFERENCES public.bots (bot_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: bots_to_ex | type: CONSTRAINT --
-- ALTER TABLE public.bot_exchanges DROP CONSTRAINT IF EXISTS bots_to_ex CASCADE;
ALTER TABLE public.bot_exchanges ADD CONSTRAINT bots_to_ex FOREIGN KEY (ex_id)
REFERENCES public.exchanges (ex_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: one_exchange_one_history | type: CONSTRAINT --
-- ALTER TABLE public.exchange_history DROP CONSTRAINT IF EXISTS one_exchange_one_history CASCADE;
ALTER TABLE public.exchange_history ADD CONSTRAINT one_exchange_one_history FOREIGN KEY (ex_id)
REFERENCES public.exchanges (ex_id) MATCH FULL
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: users_account_exchange | type: CONSTRAINT --
-- ALTER TABLE public.exchange_history DROP CONSTRAINT IF EXISTS users_account_exchange CASCADE;
ALTER TABLE public.exchange_history ADD CONSTRAINT users_account_exchange FOREIGN KEY (user_id)
REFERENCES public.users (uid) MATCH FULL
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: feed_symbol | type: CONSTRAINT --
-- ALTER TABLE public.feeds DROP CONSTRAINT IF EXISTS feed_symbol CASCADE;
ALTER TABLE public.feeds ADD CONSTRAINT feed_symbol FOREIGN KEY (symbol_id)
REFERENCES public.symbols (symbol_id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: feed_strategies | type: CONSTRAINT --
-- ALTER TABLE public.feeds DROP CONSTRAINT IF EXISTS feed_strategies CASCADE;
ALTER TABLE public.feeds ADD CONSTRAINT feed_strategies FOREIGN KEY (str_id)
REFERENCES public.strategies (str_id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: bot_id_bot_id | type: CONSTRAINT --
-- ALTER TABLE public.simulations DROP CONSTRAINT IF EXISTS bot_id_bot_id CASCADE;
ALTER TABLE public.simulations ADD CONSTRAINT bot_id_bot_id FOREIGN KEY (bot_id)
REFERENCES public.bots (bot_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --


