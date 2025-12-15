# Bella Tracer v2 - GraphRAG Gözlemlenebilirlik Platformu

![Python](https://img.shields.io/badge/Python-3.12-blue)
![RAG](https://img.shields.io/badge/AI-Graph_RAG-purple)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)

## Genel Bakış

**Bella Tracer v2**, **Graph Retrieval-Augmented Generation (GraphRAG)** ve **Neo4j** kullanarak dağıtık sistem izlerini analiz etmek ve anlamak için geliştirilmiş ileri bir gözlemlenebilirlik platformudur. Platform, sentetik günlükler oluşturur, gözlemlenebilirlik verilerinden dinamik bilgi grafikleri oluşturur ve AI ajanları tarafından desteklenen akıllı sorgulama yetenekleri sunar.

## Temel Özellikler

### 🤖 AI Destekli Sorgu Sistemi
- **LangGraph Tabanlı Ajan**: Soru optimizasyonu ve cevap sıralaması ile akıllı sorgu işleme
- **OpenAI Entegrasyonu**: Gelişmiş LLM ve gömme yetenekleri
- **Çok Aşamalı İşleme**: Soru optimizasyonu, belge alma ve anlamsal yeniden sıralama

### 📊 Bilgi Grafik Yönetimi
- **Neo4j Arka Ucu**: İlişki haritalaması için güçlü grafik veritabanı
- **Dinamik Grafik İnşası**: İzleme verilerinden otomatik düğüm ve ilişki oluşturma
- **Vektör Araması**: OpenAI gömmelemeleri ile anlamsal arama yetenekleri

### 🔄 Veri İşlem Hattı Mimarisi
- **Sentetik Veri Üretimi**: Test ve doğrulama için karmaşık iz desenleri oluşturma
- **Kafka Entegrasyonu**: Gerçek zamanlı veri akışı ve işleme
- **Prefect İş Akışları**: ETL işlemleri için düzenlenmiş veri işlem hatları

### 📈 İzleme Analizi
- **Çok Seviyeli İzleme İşleme**: Hizmet, pod ve günlük girişi korelasyonu
- **Bağlam Çıkarımı**: Gözlemlenebilirlik günlüklerinden akıllı meta veri ayrıştırma
- **İlişki Haritalaması**: İzleme hiyerarşileri ve bağımlılıkların otomatik keşfi

## Mimari

```
┌─────────────────────────────────────────────────────────┐
│      Sentetik Veri Üreticisi İşlem Hattı               │
│                                                         │
│  • Karmaşık iz desenleri oluşturur                     │
│  • Gerçekçi günlük dizileri oluşturur                 │
│  • Kafka'ya yayınlar                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
           ┌─────────────────┐
           │   Kafka Broker  │
           └─────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│      Bilgi Grafik Ayrıştırıcı İşlem Hattı              │
│                                                         │
│  • Kafka'dan izleme verilerini tüketir                 │
│  • Günlük girişlerini anlatı biçimine çevirür          │
│  • LLM çıkarımı ile bilgi grafik oluşturur             │
│  • Vektör gömmelemeleri ile Neo4j'ye saklar            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
           ┌─────────────────┐
           │   Neo4j Grafik  │
           │   + Vektörler   │
           └────────┬────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  REST API Uç Noktası  │
        │  /query - GraphRAG    │
        │  LangGraph ile Destekli│
        └───────────────────────┘
```

## Bileşenler

### Temel Modüller

| Modül | Amaç |
|-------|------|
| `api/app.py` | GraphRAG sorguları için FastAPI REST uç noktası |
| `pipelines/synthetic_data_generator.py` | Gerçekçi sentetik izler ve günlükler oluşturur |
| `pipelines/knowledge_graph_parser.py` | İzleme verilerini bilgi grafiklerine dönüştürür |
| `services/kafka.py` | Kafka üretici/tüketici yönetimi |
| `agent.py` | Sorgu işleme için LangGraph ajan düzenlemesi |
| `models.py` | İstek/yanıt doğrulaması için Pydantic modelleri |

### Veri İşleme Hattı

1. **Sentetik Veri Üretimi**: Farklı senaryoları temsil eden çeşitli iz desenleri oluşturur
2. **Kafka Akışı**: Oluşturulan günlükleri Kafka konularına yayınlar
3. **Bilgi Grafik İnşası**: Günlükleri tüketir, varlık/ilişkileri çıkarır, Neo4j grafik oluşturur
4. **Vektör İndeksleme**: Anlamsal arama için veri parçalarını gömmeler
5. **Sorgu Arayüzü**: Akıllı izleme sorgulaması için REST API sağlar

## Kurulum & Ayar

### Ön Koşullar

- Python 3.12+
- Neo4j 5.x
- Kafka 3.x (veya Docker kullanabilirsiniz)
- OpenAI API anahtarı

### Ortam Yapılandırması

Proje kökünde bir `.env` dosyası oluşturun:

```env
# Neo4j Yapılandırması
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Kafka Yapılandırması
KAFKA_BROKER=localhost:9092
KAFKA_TOPIC=data

# OpenAI Yapılandırması
OPENAI_API_KEY=api_anahtarınız_buraya
```

### Kurulum

```bash
# uv kullanarak bağımlılıkları yükle
uv sync

# Veya pip kullanarak
pip install -e .
```

### Docker Kurulumu

```bash
# Docker Compose kullanarak Neo4j ve Kafka'yı başlat
docker-compose up -d
```

## Kullanım

### 1. Neo4j Vektör İndeksi Oluştur

```bash
# Anlamsal arama için vektör indeksi oluştur
make neo4j-index

# Veya doğrudan
uv run create_neo4j_index
```

### 2. Veri İşlem Hatlarını Çalıştır

Hem sentetik veri üreticisi hem de bilgi grafik ayrıştırıcı işlem hatlarını başlat:

```bash
make run-flows
```

Veya ayrı ayrı çalıştır:

```bash
# Sentetik veri üreticisi işlem hattı
uv run synthetic_data_generator_pipeline

# Bilgi grafik ayrıştırıcı işlem hattı
uv run knowledge_graph_parser_pipeline
```

### 3. API Sunucusunu Başlat

```bash
# FastAPI sunucusunu başlat
uv run api

# Sunucu http://localhost:8000 adresinde kullanılabilir olacak
```

### 4. Sistemi Sorgula

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Son bir saat içinde hangi hizmetler başarısız oldu?"
  }'
```

## API Referansı

### POST /query

GraphRAG tarafından desteklenen akıllı sorgu uç noktası.

**İstek:**
```json
{
  "question": "string"
}
```

**Yanıt:**
```json
{
  "answer": "string",
  "original_question": "string",
  "optimized_question": "string",
  "extracted_dates": { },
  "context_sources": ["string"]
}
```

## Veri Akışı Örneği

### İzleme İşleme Aşamaları

1. **Ham Günlük Girişi** (JSON)
   ```json
   {
     "trace_id": "trace-123",
     "service_name": "api-gateway",
     "level": "ERROR",
     "message": "Veritabanı bağlantısı zaman aşımına uğradı",
     "metadata": [
       {"key": "pod_id", "value": "pod-456"},
       {"key": "db.statement", "value": "SELECT * FROM users"}
     ]
   }
   ```

2. **Anlatı Çıkarımı**
   ```
   'api-gateway' hizmeti ('pod-456' pod'unda çalışan) 
   ERROR seviyesinde günlüğe "Veritabanı bağlantısı zaman aşımına uğradı" 
   mesajını kaydetmiştir. 
   Bağlam: 'SELECT * FROM users' veritabanı sorgusu yürütüldü
   ```

3. **Bilgi Grafik Düğümleri & İlişkileri**
   - Düğümler: Service, Trace, Pod, LogEntry, Database
   - İlişkiler: PART_OF_TRACE, RUNNING_ON, EXECUTED_QUERY

## Proje Yapısı

```
bella-tracer-v2/
├── src/bella_tracer_v2/
│   ├── api/                          # FastAPI uygulaması
│   │   └── app.py
│   ├── pipelines/                    # ETL işlem hatları
│   │   ├── synthetic_data_generator.py
│   │   └── knowledge_graph_parser.py
│   ├── services/                     # Dış hizmetler
│   │   └── kafka.py
│   ├── agent.py                      # LangGraph ajan
│   ├── models.py                     # Veri modelleri
│   ├── main.py                       # Giriş noktaları
│   └── synthetic_data.py             # İz üretimi
├── artifacts/                        # Oluşturulan veri setleri
├── docker-compose.yaml               # Yerel ortam
├── Makefile                          # İnşa komutları
└── pyproject.toml                    # Proje meta verileri
```

## Teknolojiler

- **LangChain**: AI çerçevesi ve araç entegrasyonları
- **LangGraph**: Ajan düzenlemesi ve iş akışı
- **Neo4j GraphRAG**: Bilgi grafik RAG
- **FastAPI**: REST API çerçevesi
- **Prefect**: İş akışı düzenlemesi
- **Kafka**: Dağıtık akış
- **OpenAI**: LLM ve gömmeler
- **spaCy**: NLP işleme
- **Pandas**: Veri manipülasyonu

## Katkıda Bulunma

Katkılar hoş geldinir! Lütfen aşağıdakilerden emin olun:

- Kod PEP 8 standartlarına uygun
- Yeni özellikler için testler sağlanmış
- Belgeler güncellenmiş

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır - ayrıntılar için LICENSE dosyasına bakın.

## Destek

Sorunlar, sorular veya öneriler için lütfen havuzda bir sorun açın.

---

**Durum**: Beta - Aktif olarak geliştirilmekte

**Son Güncelleme**: Aralık 2025
