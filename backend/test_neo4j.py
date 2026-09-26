from app.services.neo4j_graph import Neo4jGraphService

service = Neo4jGraphService()

try:
    service.verify()
    print("Neo4j connection successful")
finally:
    service.close()