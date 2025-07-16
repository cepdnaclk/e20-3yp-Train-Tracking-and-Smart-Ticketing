import os
import pandas as pd
from django.core.management.base import BaseCommand
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Command(BaseCommand):
    help = "Reset and upload Sri Lanka railway station data to Neo4j Aura"

    def handle(self, *args, **options):
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # File paths
        station_file = "api/data/test_stations.csv"
        distance_file = "api/data/test_distance.csv"

        # Step 1: Delete all existing data
        """self.stdout.write("❌ Deleting all existing nodes and relationships...")
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        self.stdout.write(self.style.WARNING("🧹 All existing data deleted."))"""

        # Step 2: Load station data
        stations_df = pd.read_csv(station_file)

        # Step 3: Create station nodes
        self.stdout.write("🔁 Creating station nodes...")
        with driver.session() as session:
            for _, row in stations_df.iterrows():
                session.run("""
                    MERGE (s:Station {station_id: $station_id})
                    SET s.name = $name,
                        s.latitude = $latitude,
                        s.longitude = $longitude
                """, station_id=row["Station_ID"], name=row["Station Name"],
                    latitude=row["Latitude"], longitude=row["Longitude"])
                
                self.stdout.write(f"✅ Created station node: {row['Station Name']} (ID: {row['Station_ID']})")

        # Step 4: Load distance matrix and normalize names
        distance_df = pd.read_csv(distance_file, index_col=0)
        distance_df.index = distance_df.index.str.strip().str.lower()
        distance_df.columns = distance_df.columns.str.strip().str.lower()

        # Step 5: Create bi-directional relationships
        self.stdout.write("🔁 Creating route relationships...")
        with driver.session() as session:
            for source in distance_df.index:
                for target in distance_df.columns:
                    if pd.notna(distance_df.at[source, target]):
                        distance = float(distance_df.at[source, target])

                        # Create both directions
                        session.run("""
                            MATCH (a:Station), (b:Station)
                            WHERE toLower(a.name) = $from_name AND toLower(b.name) = $to_name
                            MERGE (a)-[r1:CONNECTED_TO]->(b)
                            SET r1.distance = $distance
                        """, from_name=source, to_name=target, distance=distance)

                        session.run("""
                            MATCH (a:Station), (b:Station)
                            WHERE toLower(a.name) = $from_name AND toLower(b.name) = $to_name
                            MERGE (b)-[r2:CONNECTED_TO]->(a)
                            SET r2.distance = $distance
                        """, from_name=source, to_name=target, distance=distance)

                        self.stdout.write(f"✅ Created relation: {source.title()} ↔ {target.title()} ({distance} km)")

        self.stdout.write(self.style.SUCCESS("🎉 All station nodes and route relationships created."))
