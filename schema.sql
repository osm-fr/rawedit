--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: session; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE session (
    date timestamp without time zone NOT NULL,
    id character varying(64) NOT NULL,
    request_token_key character varying(64),
    request_token_secret character varying(64),
    access_token_key character varying(64),
    access_token_secret character varying(64),
    data_changeset bigint,
    data_uri character varying(1024)
);


--
-- PostgreSQL database dump complete
--

