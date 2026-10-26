from src.db import initialize
import argparse
p=argparse.ArgumentParser();p.add_argument('--reset',action='store_true');args=p.parse_args()
initialize(reset=args.reset)
print('Synthetic SQLite database ready. Reset:',args.reset)
