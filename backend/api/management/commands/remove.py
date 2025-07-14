from django.core.management.base import BaseCommand
import redis

class Command(BaseCommand):
    help = 'Remove all Redis cached train location data'

    def handle(self, *args, **kwargs):
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.flushdb()
        self.stdout.write(self.style.SUCCESS('✅ All Redis cached train locations removed successfully.'))
