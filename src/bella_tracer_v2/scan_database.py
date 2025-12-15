import json
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def scan_database():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    report = {
        "node_labels": [],
        "relationship_types": [],
        "sample_connections": [],
        "node_properties_sample": {},
    }

    try:
        print("🔍 Veritabanı taranıyor...")

        # 1. Node Etiketlerini (Labels) Çek
        print("- Node tipleri alınıyor...")
        labels_result = driver.execute_query("CALL db.labels()")
        report["node_labels"] = [r[0] for r in labels_result.records]

        # 2. İlişki Tiplerini (Relationship Types) Çek
        print("- İlişki tipleri alınıyor...")
        rels_result = driver.execute_query("CALL db.relationshipTypes()")
        report["relationship_types"] = [r[0] for r in rels_result.records]

        # 3. Örnek Bağlantılar (Kimin eli kimin cebinde?)
        # İlişki isimlerini bilmeden (a)-[r]->(b) şeklinde tarıyoruz.
        print("- Örnek bağlantılar taranıyor...")
        sample_query = """
        MATCH (a)-[r]->(b)
        WITH a, r, b LIMIT 20
        RETURN 
            labels(a) as source_labels, 
            type(r) as rel_type, 
            labels(b) as target_labels,
            properties(a) as source_props,
            properties(b) as target_props
        """
        samples_result, _, _ = driver.execute_query(sample_query)

        for record in samples_result:
            # Prop'ları kısaltalım ki çıktı çok şişmesin
            src_props = record["source_props"]
            tgt_props = record["target_props"]

            # Sadece fikir vermesi için ilk 2-3 key'i alalım veya ID/Name varsa onları
            summary = {
                "pattern": f"({record['source_labels'][0]}) -[:{record['rel_type']}]-> ({record['target_labels'][0]})",
                "source_sample": {k: v for k, v in list(src_props.items())[:3]},
                "target_sample": {k: v for k, v in list(tgt_props.items())[:3]},
            }
            report["sample_connections"].append(summary)

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
    finally:
        driver.close()
        print("✅ Tarama bitti.")

    # Sonucu JSON olarak bas
    print("\n--- NEO4J SCAN RESULT START ---")
    # Save to file (env var to override path)
    output_path = os.getenv("NEO4J_SCAN_REPORT", "neo4j_scan_report.json")
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"Report saved to: {output_path}")
    # Also print a compact JSON summary to stdout
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("--- NEO4J SCAN RESULT END ---")


if __name__ == "__main__":
    scan_database()
