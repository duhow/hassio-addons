#!/usr/bin/env python3

import json
import gc
import os
import sys
import asyncio
import pathlib
import websockets
import concurrent.futures
import logging
import argparse

from vosk import Model, KaldiRecognizer

LOG_LEVELS = ["WARNING", "INFO", "DEBUG"]

def process_chunk(rec, message):
    if message == '{"eof" : 1}':
        return rec.FinalResult(), True
    elif rec.AcceptWaveform(message):
        return rec.Result(), False
    else:
        return rec.PartialResult(), False

async def recognize(websocket, path):
    global loop
    global pool
    global model

    rec = None
    phrase_list = None
    sample_rate = args.sample_rate
    show_words = not args.hide_words
    max_alternatives = args.alternatives

    logging.info('Connection from %s', websocket.remote_address);

    while True:

        message = await websocket.recv()

        # Load configuration if provided
        if isinstance(message, str) and 'config' in message:
            jobj = json.loads(message)['config']
            logging.info("Config %s", jobj)
            if 'phrase_list' in jobj:
                phrase_list = jobj['phrase_list']
            if 'sample_rate' in jobj:
                sample_rate = float(jobj['sample_rate'])
            if 'words' in jobj:
                show_words = bool(jobj['words'])
            if 'max_alternatives' in jobj:
                max_alternatives = int(jobj['max_alternatives'])
            if 'model' in jobj:
                model_path = str(jobj['model'])
                parent_path = pathlib.Path(args.model_path) / '..' / model_path

                if pathlib.Path(model_path).exists():
                    model = Model(str(pathlib.Path(model_path)))
                    logging.info(f"Using relative path {model}")
                elif parent_path.exists():
                    model = Model(str(parent_path))
                    logging.info(f"Using parent path {model}")
                else:
                    logging.warning(f"Model {model} not available")
                # use garbage collector to clean previous models
                gc.collect()

            continue

        # Create the recognizer, word list is temporary disabled since not every model supports it
        if not rec:
            logging.debug("Setting KaldiRecognizer")

            if phrase_list:
                 rec = KaldiRecognizer(model, sample_rate, json.dumps(phrase_list, ensure_ascii=False))
            else:
                 rec = KaldiRecognizer(model, sample_rate)
            #rec.SetWords(show_words)
            rec.SetMaxAlternatives(max_alternatives)

        response, stop = await loop.run_in_executor(pool, process_chunk, rec, message)
        await websocket.send(response)
        if stop: break

def parser():
    args = argparse.ArgumentParser(
        description="Vosk-Server websocket listener",
        prog="Vosk-Server"
    )
    args.add_argument(
        '-i', '--bind',
        default=os.environ.get('VOSK_SERVER_INTERFACE', '0.0.0.0'),
        help="IP address to bind"
    )
    args.add_argument(
        '-p', '--port',
        type=int,
        default=os.environ.get('VOSK_SERVER_PORT', 2700),
        help="Port to listen for websocket server"
    )
    args.add_argument(
        '-r', '--sample-rate',
        type=int,
        default=os.environ.get('VOSK_SAMPLE_RATE', 8000),
        help="Sample rate to use"
    )
    args.add_argument(
        '-a', '--alternatives',
        type=int,
        default=os.environ.get('VOSK_ALTERNATIVES', 0),
        help="Amount of alternative words to present"
    )
    args.add_argument(
        '--hide-words',
        action="store_false",
        help="Hide word display"
    )
    args.add_argument(
        'model_path',
        default=os.environ.get('VOSK_MODEL_PATH', 'model'),
        type=pathlib.Path,
        help="Path to model folder"
    )
    args.add_argument(
        '--gpu',
        action="store_true",
        help="Enable GPU usage"
    )
    args.add_argument(
        '-v', '--verbose',
        action="count",
        default=0,
        help="Set logging level"
    )
    args.add_argument(
        '-V', '--version',
        action="version",
        version="%(prog)s 0.3.27"
    )
    return args

def start():
    global args
    global loop
    global pool

    if args.gpu:
        from vosk import GpuInit, GpuInstantiate
        GpuInit()
        def thread_init():
            GpuInstantiate()
        pool = concurrent.futures.ThreadPoolExecutor(initializer=thread_init)
    else:
        pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))

    loop = asyncio.get_event_loop()

    start_server = websockets.serve(recognize, args.bind, args.port)

    logging.info(f"Listening on {args.bind}:{args.port}")
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == '__main__':
    args = parser().parse_args()
    args.verbose = min(args.verbose, len(LOG_LEVELS) - 1)

    logging.basicConfig(level=LOG_LEVELS[args.verbose])
    model = Model(str(args.model_path))

    start()
