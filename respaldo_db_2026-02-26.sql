--
-- PostgreSQL database dump
--

\restrict WhpXvF4c5umraobQJE3ewYIbuS3WsLbNEKO0Pd7SieXFPYUVm3YreSsnnqWCHUX

-- Dumped from database version 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: pago; Type: TABLE; Schema: public; Owner: luciernaga_user
--

CREATE TABLE public.pago (
    id integer NOT NULL,
    payment_id character varying(64) NOT NULL,
    email character varying(255),
    fotos json,
    token character varying(64),
    expira integer,
    created_at integer,
    descargado boolean DEFAULT false
);


ALTER TABLE public.pago OWNER TO luciernaga_user;

--
-- Name: pago_id_seq; Type: SEQUENCE; Schema: public; Owner: luciernaga_user
--

CREATE SEQUENCE public.pago_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pago_id_seq OWNER TO luciernaga_user;

--
-- Name: pago_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: luciernaga_user
--

ALTER SEQUENCE public.pago_id_seq OWNED BY public.pago.id;


--
-- Name: pago id; Type: DEFAULT; Schema: public; Owner: luciernaga_user
--

ALTER TABLE ONLY public.pago ALTER COLUMN id SET DEFAULT nextval('public.pago_id_seq'::regclass);


--
-- Data for Name: pago; Type: TABLE DATA; Schema: public; Owner: luciernaga_user
--

COPY public.pago (id, payment_id, email, fotos, token, expira, created_at, descargado) FROM stdin;
6	146537262909	juan_alonso_andrade@hotmail.com	["IMG_0482.jpg"]	P5HAy2mcFMCwVCtSPwQT6ZKIB1-C4WD2gzWZANZ2sQA	1771882233	1771709433	t
8	147275358528	zzaguirre@hotmail.com	["IMG_0482.jpg", "IMG_0481.jpg"]	btpWD7Hei5dhTcJIwYR1Tqtm9HPDVMGV-cyt04gYyVg	1771900165	1771727365	t
10	147280314020	zzaguirre@hotmail.com	["IMG_0488.jpg"]	_g1ovbLwv_I6L0FALEWLbIoXwKPDXHekNUIR8cJvD7o	1771904433	1771731633	t
12	146581168829	zzaguirre@hotmail.com	["IMG_0500.jpg"]	aGlbFF2cSHMBzXxUzj_OyWWRsBOkt2elHN0bVddZBrE	1771905527	1771732727	t
4	147237117074	juan_alonso_andrade@hotmail.com	["IMG_0482.jpg"]	WiJAydicZ_bk3kJqiNiEidVrQw5z1CmY-ylmMEMFr_0	1771882096	1771709296	t
14	147503363808	zzaguirre@hotmail.com	["cinthyaRene188.jpg"]	JnYySAU75vrOBIemPLJwVcryJCbLTro7Mpdawt8pyYk	1772064479	1771891679	t
2	147224797312	juan_alonso_andrade@hotmail.com	["IMG_0483.jpg"]	Ew8OR2KvSkwHQeFIVCPqI_FUrYzqVq9saTWW_5nocXc	1771876296	1771703496	t
3	147232964756	juan_alonso_andrade@hotmail.com	["IMG_0482.jpg"]	caG9e7Iw8xX-7QUcjd68Xj-F-opzdEXJ8bLkYdTBKIc	1771880264	1771707464	t
1	146452167061	juan_alonso_andrade@hotmail.com	["IMG_0483.jpg"]	iQ7-EJeUXQiSz7Whinj7bzj1RDWtYfDfuFcJgBgUkIo	1771876376	1771647760	t
17	147084786015	jdjdud@hotmail.com	["Almerinaoscar1_3.jpg"]	blnsx2xgy0igFkIA_XYKe-TzK36ObUC-Jeir6i1nKq0	1772240574	1772067774	f
16	147083783973	zzaguirre@hotmail.com	["cinthyaRene188_2.jpg"]	2VAMbF-8pLvEukCLl7CAuVU5cPRd7MoIlBEA5crplpI	1772239930	1772067130	t
18	147085625609	huuu@gmail.com	["cinthyaRene188-2_1.jpg"]	RnbD-kXjXJDizn5KZefdysiUpDuK-dqirWYf8n8Hi50	1772241017	1772068217	f
19	147087073277	juan_alonso_andrade@hotmail.com	["cinthyaRene188-2_1.jpg"]	0Ynebc7QzTrrr4RkdzkTPbkdf1KCoR0mpnEYIgAxSD4	1772242006	1772069206	f
\.


--
-- Name: pago_id_seq; Type: SEQUENCE SET; Schema: public; Owner: luciernaga_user
--

SELECT pg_catalog.setval('public.pago_id_seq', 19, true);


--
-- Name: pago pago_payment_id_key; Type: CONSTRAINT; Schema: public; Owner: luciernaga_user
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_payment_id_key UNIQUE (payment_id);


--
-- Name: pago pago_pkey; Type: CONSTRAINT; Schema: public; Owner: luciernaga_user
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_pkey PRIMARY KEY (id);


--
-- Name: pago pago_token_key; Type: CONSTRAINT; Schema: public; Owner: luciernaga_user
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_token_key UNIQUE (token);


--
-- PostgreSQL database dump complete
--

\unrestrict WhpXvF4c5umraobQJE3ewYIbuS3WsLbNEKO0Pd7SieXFPYUVm3YreSsnnqWCHUX

