"""Run with DATABASE_URL set privately: python -m website.backend.tools.migrate_practice"""
import os
from website.backend.practice.bank import load_bank
from website.backend.practice.store import Store

if __name__=='__main__':
    store=Store(os.environ['DATABASE_URL'])
    store.migrate()
    store.seed(load_bank())
    print('Practice migrations and exercise seed completed.')
