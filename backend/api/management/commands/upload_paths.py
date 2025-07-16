import csv
import os
from django.core.management.base import BaseCommand
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Command(BaseCommand):
    help = "Upload SERVES_ROUTE relationships (train schedules) to Neo4j"

    def handle(self, *args, **options):
        file_path = "api/data/test_route.csv"  # Update if needed

        if not os.path.exists(file_path):
            self.stderr.write(f"❌ File not found: {file_path}")
            return

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t' if '\t' in csvfile.read(1024) else ',')
            csvfile.seek(0)

            # Organize by route_id
            routes = {}
            for row in reader:
                route_id = row['Route_ID'].strip()
                station = {
                    'station_id': int(row['Station_ID']),
                    'station_name': row['Station_name'].strip(),
                    'arrival': row['Arrival Time'].strip() if row['Arrival Time'].strip() != '—' else None,
                    'departure': row['Departure Time'].strip() if row['Departure Time'].strip() != '—' else None
                }
                routes.setdefault(route_id, []).append(station)

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            for route_id, stations in routes.items():
                for i in range(len(stations) - 1):
                    from_station = stations[i]
                    to_station = stations[i + 1]
                    sequence = i + 1

                    session.run("""
                        MATCH (a:Station {station_id: $from_id}), (b:Station {station_id: $to_id})
                        MERGE (a)-[r:SERVES_ROUTE {
                            route_id: $route_id,
                            sequence: $sequence
                        }]->(b)
                        SET r.arrival_time = $arrival_time,
                            r.departure_time = $departure_time
                    """, 
                    from_id=from_station['station_id'],
                    to_id=to_station['station_id'],
                    route_id=route_id,
                    sequence=sequence,
                    arrival_time=to_station['arrival'],
                    departure_time=from_station['departure']
                    )

                    self.stdout.write(f"✅ Added route {route_id}: {from_station['station_name']} ➜ {to_station['station_name']}")

        self.stdout.write(self.style.SUCCESS("🎉 All train schedule relationships uploaded successfully!"))
