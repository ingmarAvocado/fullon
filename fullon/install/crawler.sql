-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 1.1.3
-- PostgreSQL version: 16.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: crawler | type: DATABASE --
-- DROP DATABASE IF EXISTS crawler;
CREATE DATABASE crawler;
-- ddl-end --


CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
-- object: public.sites_follows | type: TABLE --
-- DROP TABLE IF EXISTS public.sites_follows CASCADE;
CREATE TABLE public.sites_follows (
	fid serial NOT NULL,
	uid integer NOT NULL,
	site text NOT NULL,
	account text NOT NULL,
	ranking smallint NOT NULL DEFAULT 1,
	contra bool NOT NULL DEFAULT False,
	expertise text NOT NULL,
	CONSTRAINT unique_fid PRIMARY KEY (fid),
	CONSTRAINT "onefuid-oneuid" UNIQUE (uid,site,account)
);
-- ddl-end --
ALTER TABLE public.sites_follows OWNER TO postgres;
-- ddl-end --

-- object: public.cat_sites | type: TABLE --
-- DROP TABLE IF EXISTS public.cat_sites CASCADE;
CREATE TABLE public.cat_sites (
	sites text NOT NULL,
	CONSTRAINT one_site_only PRIMARY KEY (sites)
);
-- ddl-end --
ALTER TABLE public.cat_sites OWNER TO postgres;
-- ddl-end --

-- object: public.sites_posts | type: TABLE --
-- DROP TABLE IF EXISTS public.sites_posts CASCADE;
CREATE TABLE public.sites_posts (
	post_id serial NOT NULL,
	"timestamp" timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
	remote_id bigint NOT NULL,
	account text NOT NULL,
	account_id bigint NOT NULL,
	site text NOT NULL,
	content text NOT NULL,
	media text,
	media_ocr text,
	urls text,
	is_reply bool NOT NULL DEFAULT False,
	reply_to bigint,
	self_reply bool NOT NULL DEFAULT False,
	views integer NOT NULL,
	likes integer NOT NULL,
	reposts integer NOT NULL,
	replies integer NOT NULL,
	followers integer NOT NULL,
	pre_score numeric,
	score numeric,
	CONSTRAINT primary_key PRIMARY KEY (post_id),
	CONSTRAINT remote_id_site_unique UNIQUE (remote_id,site)
);
-- ddl-end --
ALTER TABLE public.sites_posts OWNER TO postgres;
-- ddl-end --

-- object: public.post_analyzers | type: TABLE --
-- DROP TABLE IF EXISTS public.post_analyzers CASCADE;
CREATE TABLE public.post_analyzers (
	aid serial NOT NULL,
	title text NOT NULL,
	prompt text NOT NULL,
	CONSTRAINT analyzer_pk PRIMARY KEY (aid)
);
-- ddl-end --
ALTER TABLE public.post_analyzers OWNER TO postgres;
-- ddl-end --

-- object: public.engine_scores | type: TABLE --
-- DROP TABLE IF EXISTS public.engine_scores CASCADE;
CREATE TABLE public.engine_scores (
	aid integer NOT NULL,
	post_id smallint NOT NULL,
	engine text NOT NULL,
	score numeric NOT NULL,
	CONSTRAINT one_post_one_engine UNIQUE (post_id,engine,aid)
);
-- ddl-end --
ALTER TABLE public.engine_scores OWNER TO postgres;
-- ddl-end --

-- object: public.llm_engines | type: TABLE --
-- DROP TABLE IF EXISTS public.llm_engines CASCADE;
CREATE TABLE public.llm_engines (
	engine text NOT NULL,
	CONSTRAINT llm_engines_pk PRIMARY KEY (engine)
);
-- ddl-end --
ALTER TABLE public.llm_engines OWNER TO postgres;
-- ddl-end --

-- object: public.follows_analyzers | type: TABLE --
-- DROP TABLE IF EXISTS public.follows_analyzers CASCADE;
CREATE TABLE public.follows_analyzers (
	uid integer NOT NULL,
	aid integer NOT NULL,
	fid integer NOT NULL,
	account text NOT NULL

);
-- ddl-end --
ALTER TABLE public.follows_analyzers OWNER TO postgres;
-- ddl-end --

-- object: site_one_site | type: CONSTRAINT --
-- ALTER TABLE public.sites_follows DROP CONSTRAINT IF EXISTS site_one_site CASCADE;
ALTER TABLE public.sites_follows ADD CONSTRAINT site_one_site FOREIGN KEY (site)
REFERENCES public.cat_sites (sites) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: site_name_site_name2 | type: CONSTRAINT --
-- ALTER TABLE public.sites_posts DROP CONSTRAINT IF EXISTS site_name_site_name2 CASCADE;
ALTER TABLE public.sites_posts ADD CONSTRAINT site_name_site_name2 FOREIGN KEY (site)
REFERENCES public.cat_sites (sites) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: engine_pid_pid | type: CONSTRAINT --
-- ALTER TABLE public.engine_scores DROP CONSTRAINT IF EXISTS engine_pid_pid CASCADE;
ALTER TABLE public.engine_scores ADD CONSTRAINT engine_pid_pid FOREIGN KEY (post_id)
REFERENCES public.sites_posts (post_id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: llm_engines_post | type: CONSTRAINT --
-- ALTER TABLE public.engine_scores DROP CONSTRAINT IF EXISTS llm_engines_post CASCADE;
ALTER TABLE public.engine_scores ADD CONSTRAINT llm_engines_post FOREIGN KEY (engine)
REFERENCES public.llm_engines (engine) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: aid_to_aid | type: CONSTRAINT --
-- ALTER TABLE public.engine_scores DROP CONSTRAINT IF EXISTS aid_to_aid CASCADE;
ALTER TABLE public.engine_scores ADD CONSTRAINT aid_to_aid FOREIGN KEY (aid)
REFERENCES public.post_analyzers (aid) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: aid_follows_engine | type: CONSTRAINT --
-- ALTER TABLE public.follows_analyzers DROP CONSTRAINT IF EXISTS aid_follows_engine CASCADE;
ALTER TABLE public.follows_analyzers ADD CONSTRAINT aid_follows_engine FOREIGN KEY (aid)
REFERENCES public.post_analyzers (aid) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: fid_follows_engine | type: CONSTRAINT --
-- ALTER TABLE public.follows_analyzers DROP CONSTRAINT IF EXISTS fid_follows_engine CASCADE;
ALTER TABLE public.follows_analyzers ADD CONSTRAINT fid_follows_engine FOREIGN KEY (fid)
REFERENCES public.sites_follows (fid) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --


