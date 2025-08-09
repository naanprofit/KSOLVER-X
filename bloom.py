#-------------------------------------------------------------------------
# Name:        BLOOM FOR KSOLVER X
# Author:      pianist (Telegram: @pianist_coder)
# Credit:      iceland
# Created:     24.05.2024
# Copyright:   (c) pianist 2022-2024
#-------------------------------------------------------------------------

import os, sys, xxhash, random, time
import secp256k1 as btc
from pybloomfilter import BloomFilter
from sys import argv
from multiprocessing import Process, cpu_count, Value, Event
from base128 import encode_base128

#=========================================================================
class color:
    GREEN = '\033[32m'
    RED = '\033[31m'
    X = '\033[5m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
#=========================================================================
bsplash = '''
█▀▄ █░░ ▄▀▄ ▄▀▄ █▄░▄█     █▀ ▀ █░░ ▀█▀ █▀▀ █▀▀▄ 
█▀█ █░▄ █░█ █░█ █░█░█     █▀ █ █░▄ ░█░ █▀▀ █▐█▀ 
▀▀░ ▀▀▀ ░▀░ ░▀░ ▀░░░▀     ▀░ ▀ ▀▀▀ ░▀░ ▀▀▀ ▀░▀▀ 
'''
#=========================================================================
(count, bloom_filter_name, filebase, bit, core) = (int(argv[1]), argv[2], argv[3], int(argv[4]), int(argv[5]))
start = bit - 1
end = bit
if os.path.exists(bloom_filter_name):
    bf = BloomFilter.open(bloom_filter_name)
else:
    bf = BloomFilter(count, 0.0000000001, bloom_filter_name)
st = time.time()
#=========================================================================

def pr():
    os.system('cls||clear')
    print(color.GREEN + bsplash + color.END)
    print(color.RED + 'by pianist (Telegram: @pianist_coder | btc: bc1q0jth0rjaj2vqtqgw45n39fg4qrjc37hcw4frcz)' + color.END)
    print(color.BOLD + '\n[+] Program started' + color.END)
    print("-"*87)
    print(f'[+] Items: {count}')
    print(f'[+] Cores: {core}')
    print("-"*87)
    
def generate_random_batch(start, end, size=10000):
    """Generate a batch of random private keys and their public points."""
    keys = [random.randint(2 ** start - (2 ** start - 5), 2 ** end - 1) for _ in range(size)]
    points = btc.scalar_multiplications(keys)
    return keys, points

def scan_str(num):
    suffixes = ["", "K", "M", "B", "T"]
    exponent = 0
    while abs(num) >= 1000 and exponent < 4:
        num /= 1000
        exponent += 1
    return f"{num:.2f} {suffixes[exponent]}"

def display_time(seconds):
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"

def speedup(st, counter):
    speed = counter / (time.time() - st)
    print(f'[{scan_str(counter)}] [{scan_str(speed)}keys] [{display_time(time.time() - st)}]      ', end = '\r')
    
def bloom_start(cores='all'):
    try:
        available_cores = cpu_count()
        if cores == 'all': cores = available_cores
        elif 0 < int(cores) <= available_cores: cores = int(cores)
        else: cores = 1
        counter = Value('L')
        workers = []
        match = Event()
        for r in range(cores):
            p = Process(target=bloom_create, args=(counter, r, match))
            workers.append(p)
            p.start()
        for worker in workers:
            worker.join()
    except(KeyboardInterrupt, SystemExit):
        exit('\nSIGINT or CTRL-C detected. Exiting gracefully. BYE')
    sys.stdout.write('\n\n[+] Bloom creating complete in {0:.2f} sec\n'.format(time.time() - st))

def save_data(keys, points, filename):
    with open(filename, "ab", buffering=0) as f:
        for i, key in enumerate(keys):
            item = points[i*65:(i+1)*65]
            f.write(encode_base128(key) + xxhash.xxh64(item).digest())
            bf.add(item)
    bf.flush()
            
def bloom_create(counter, r, match):
    st = time.time()
    while not match.is_set():
        if match.is_set(): return
        keys, points = generate_random_batch(start, end)
        save_data(keys, points, filebase)
        with counter.get_lock(): counter.value += len(keys)
        if counter.value % 1000000 == 0:
            speedup(st, counter.value)
        if counter.value == count - (core-1)*10000:
            match.set()

            
#=========================================================================
pr()
bloom_start(cores=core)

'''

use:

pip install pybloomfiltermmap3
pip install xxhash
python3 bloom.py 10000000 60 60.txt 60 10

'''
