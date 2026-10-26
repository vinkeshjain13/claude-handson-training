import argparse, getpass
from src.core import init_db,register_reviewer,DB_PATH

def main():
 p=argparse.ArgumentParser();p.add_argument('--reset',action='store_true');args=p.parse_args()
 init_db(reset=args.reset)
 print('Database:',DB_PATH)
 print('Create your local human-reviewer credential (never provide it to Claude).')
 username=input('Reviewer username: ').strip()
 pw=getpass.getpass('Reviewer passphrase (12+ characters): ')
 register_reviewer(username,pw)
 print('Reviewer registered. Seed transactions: TX1001 TX1002 TX1003')
if __name__=='__main__':main()
