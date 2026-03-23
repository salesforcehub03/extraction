
// ==========================================
// Neo4j Visualization & Exploration Queries
// ==========================================
// Copy and paste these queries into the Neo4j Browser bar (one by one) to view your data.

// 1. View the entire graph (Limited to 300 nodes for performance)
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 300;

// 2. View the Schema (Meta-Graph) to see how Node Types match up
CALL db.schema.visualization();

// 3. Focus on "Belinostat" and its direct connections
MATCH (d:Drug {name: "Belinostat"})-[r]-(connected_node)
RETURN d, r, connected_node;

// 4. View all "Target" nodes (e.g., HDACs) and their properties
MATCH (t:Target)
RETURN t;

// 5. Visualizing the Genomic Data (HDACs with Chromosome info)
MATCH (t:Target)
WHERE t.name CONTAINS "HDAC"
RETURN t;

// 6. View Adverse Events caused by Belinostat (Filtered by High Confidence)
MATCH (d:Drug)-[r:causes]->(ae:Adverse_Event)
WHERE r.confidence > 0.8
RETURN d, r, ae;

// 7. Find shared connections (e.g., AEs observed in multiple groups/studies)
MATCH (g1)-[:observed_in]->(ae:Adverse_Event)<-[:observed_in]-(g2)
RETURN g1, ae, g2;

// 8. Count nodes by Type (Statistics)
MATCH (n)
RETURN labels(n) as Type, count(n) as Count
ORDER BY Count DESC;
