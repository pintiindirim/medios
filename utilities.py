from dependencies import *
from numba import njit
import re
import urllib.parse

def flush_logs():
    for handler in logger.handlers:
        handler.flush()

@njit
def compute_difference(p_price, ak_price):
    return p_price - ak_price

def turkishize(text):
    logger.debug("turkishize: Girdi: %s", text)
    flush_logs()
    mapping = {
        "akilli": "akıllı",
        "sari": "sarı",
        "kirmizi": "kırmızı",
        "titanyum": "Titan"
    }
    for eng, tr in mapping.items():
        text = text.replace(eng, tr)
    logger.debug("turkishize: Çıktı: %s", text)
    flush_logs()
    return text

def adjust_product_name_for_akakce(text):
    logger.debug("adjust_product_name_for_akakce: Girdi: %s", text)
    flush_logs()
    text = turkishize(text)
    text = re.sub(r'(\d+)\s*[Gg][Bb]', r'\1 GB', text)
    text = re.sub(r'\bAkıllı Telefon\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Mint\s+Yeşil\b', 'Mint Yeşili', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if text.lower().endswith("antrasit"):
        text = re.sub(r'\s*antrasit\s*$', '', text, flags=re.IGNORECASE) + " Grafit"
    logger.debug("adjust_product_name_for_akakce: Çıktı: %s", text)
    flush_logs()
    return text

def process_xiaomi_capacity(token, all_tokens):
    if len(token) == 5:
        ram = token[:2]
        storage = token[2:]
    elif len(token) == 4:
        ram = token[:1]
        storage = token[1:]
    else:
        storage = token
        ram = ""
    lower_tokens = [t.lower() for t in all_tokens]
    if "14t" in lower_tokens:
        return f"{int(storage)} GB"   
    if "xiaomi" in lower_tokens or "redmi" in lower_tokens:
        if "note" in lower_tokens and "pro" in lower_tokens:
            if "5g" in lower_tokens:
                return f"{int(storage)} GB"
            else:
                return f"{int(storage)} GB {int(ram)} GB"
        elif "14c" in lower_tokens:
            return f"{int(storage)} GB {int(ram)} GB"
        elif "13" in lower_tokens:
            return f"{int(storage)} GB"
        else:
            if int(ram) > 0:
                return f"{int(storage)} GB {int(ram)} GB"
            else:
                return f"{int(storage)} GB"
    else:
        return f"{int(token)} GB"

def adjust_xiaomi_product_name(product_name: str, url: str = None) -> str:
    logger.debug("adjust_xiaomi_product_name: Girdi -> product_name: '%s', url: '%s'", product_name, url)
    flush_logs()
    xiaomi_name_mapping = {
        "1240637": "Xiaomi 14T 256 GB Titan Grisi",
        "1240639": "Xiaomi 14T 256 GB Titan Mavisi",
        "1240629": "Xiaomi 14T 256 GB Titan Siyahı",
        "1240641": "Xiaomi 14T Pro 512 GB Titan Grisi",
        "1240648": "Xiaomi 14T Pro 512 GB Titan Mavisi",
        "1240640": "Xiaomi 14T Pro 512 GB Titan Siyahı",
        "1237972": "Xiaomi Redmi 13 256 GB Mavi",
        "1237971": "Xiaomi Redmi 13 256 GB Altın",
        "1237970": "Xiaomi Redmi 13 256 GB Siyah",
        "1241459": "Xiaomi Redmi 14C 256 GB 8 GB Mavi",
        "1241461": "Xiaomi Redmi 14C 256 GB 8 GB Mavi",
        "1241460": "Xiaomi Redmi 14C 256 GB 8 GB Yeşil",
        "1243825": "Xiaomi Redmi Note 14 256 GB Mavi",
        "1243824": "Xiaomi Redmi Note 14 256 GB Mor",
        "1243826": "Xiaomi Redmi Note 14 256 GB Siyah",
        "1243777": "Xiaomi Redmi Note 14 Pro 256 GB 8 GB Mavi",
        "1243776": "Xiaomi Redmi Note 14 Pro 256 GB 8 GB Mor",
        "1243823": "Xiaomi Redmi Note 14 Pro 256 GB 8 GB Siyah",
        "1243774": "Xiaomi Redmi Note 14 Pro 512 GB 12 GB Mavi",
        "1243773": "Xiaomi Redmi Note 14 Pro 512 GB 12 GB Mor",
        "1243775": "Xiaomi Redmi Note 14 Pro 512 GB 12 GB Siyah",
        "1243768": "Xiaomi Redmi Note 14 Pro Plus 512 GB Mavi",
        "1243770": "Xiaomi Redmi Note 14 Pro 5G 512 GB Mor",
        "1243767": "Xiaomi Redmi Note 14 Pro Plus 512 GB Mor",
        "1243772": "Xiaomi Redmi Note 14 Pro 5G 512 GB Siyah",
        "1243769": "Xiaomi Redmi Note 14 Pro Plus 512 GB Siyah",
        "1243771": "Xiaomi Redmi Note 14 Pro 5G 512 GB Yeşil"
    }
    if url:
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path  
            logger.debug("adjust_xiaomi_product_name: Parsed path: %s", path)
            flush_logs()
            parts = path.split('-')
            if parts:
                last_part = parts[-1]
                product_id = last_part.replace('.html', '')
                logger.debug("adjust_xiaomi_product_name: Çıkarılan ürün ID: %s", product_id)
                flush_logs()
                if product_id in xiaomi_name_mapping:
                    logger.info("adjust_xiaomi_product_name: Mapping bulundu, ürün ID: %s, isim: %s",
                                product_id, xiaomi_name_mapping[product_id])
                    flush_logs()
                    return xiaomi_name_mapping[product_id]
                else:
                    logger.warning("adjust_xiaomi_product_name: Ürün ID: %s için mapping bulunamadı.", product_id)
                    flush_logs()
        except Exception as e:
            logger.error("adjust_xiaomi_product_name: URL'den ürün ID'si çıkarılırken hata: %s", e)
            flush_logs()
    logger.info("adjust_xiaomi_product_name: URL bilgisi mevcut değil veya mapping bulunamadı. Genel düzenleme uygulanıyor.")
    flush_logs()
    final_name = adjust_product_name_for_akakce(product_name)
    return final_name

def adjust_oppo_product_name(product_name: str, url: str = None) -> str:
    oppo_name_mapping = {
        "1245685": "Oppo Reno 13 Pro 512 GB Grafit",
        "1245684": "Oppo Reno 13 Pro 512 GB Eflatun",
        "1245683": "Oppo Reno 13 F 5G 256 GB Grafit",
        "1245687": "Oppo Reno 13 F 5G 256 GB Eflatun",
        "1245682": "Oppo Reno 13 F 256 GB Grafit",
        "1240681": "Oppo Reno 11 FS 256 GB Yeşil",
        "1240680": "Oppo Reno 11 FS 256 GB Gri",
        "1237555": "Oppo Reno 11 F 256 GB Yeşil",
        "1238830": "Oppo A60 256 GB Mor",
        "1242760": "Oppo A3 128 GB Siyah",
        "1242759": "Oppo A3 128 GB Beyaz",
        "1245686": "Oppo Reno 13 F 256 GB Eflatun",
        "1240225": "Oppo A60 128 GB Mavi",
        "1240226": "Oppo A60 128 GB Mor",
        "1238831": "Oppo A60 256 GB Mavi",
        "1240709": "Oppo Reno 11 FS 256 GB Turuncu",
    }
    if url:
        try:
            parsed = urllib.parse.urlparse(url)
            path_parts = parsed.path.split('-')
            if path_parts:
                last_part = path_parts[-1]
                product_id = last_part.replace(".html", "")
                logger.debug("adjust_oppo_product_name: Tespit edilen ürün ID'si: %s", product_id)
                flush_logs()
                if product_id in oppo_name_mapping:
                    correct_name = oppo_name_mapping[product_id]
                    logger.info("adjust_oppo_product_name: Ürün ID'si %s için akakçe adı bulundu: %s", product_id, correct_name)
                    flush_logs()
                    return correct_name
                else:
                    logger.warning("adjust_oppo_product_name: Ürün ID'si %s için eşleşme bulunamadı.", product_id)
                    flush_logs()
        except Exception as e:
            logger.error("adjust_oppo_product_name: URL'den ürün ID'si çıkarılırken hata: %s", e)
            flush_logs()
    return product_name

def adjust_realme_product_name(product_name: str, url: str = None) -> str:
    realme_name_mapping = {
        "1240684": "Realme Note 60 128 GB 4 GB Siyah",
        "1240682": "Realme Note 60 128 GB 4 GB Mavi",
        "1243729": "Realme GT 7 Pro 512 GB",
        "1238608": "Realme GT 6 512 GB 16 GB Gümüş",
        "1244663": "Realme C75 256 GB Sarı",
        "1244666": "Realme C75 256 GB Siyah",
        "1244664": "Realme C75 128 GB Sarı",
        "1244667": "Realme C75 128 GB Siyah",
        "1238612": "Realme C61 256 GB 8 GB Yeşil",
        "1238611": "Realme C61 256 GB 8 GB Altın",
        "1238614": "Realme C61 128 GB 6 GB Yeşil",
        "1238613": "Realme C61 128 GB 6 GB Altın",
        "1236635": "Realme 12 Pro Plus 512 GB 12 GB Mavi",
        "1236632": "Realme 12 Pro Plus 256 GB 8 GB Bej",
        "1236634": "Realme 12 Pro Plus 512 GB 12 GB Bej",
        "1236735": "Realme 12 Pro 256 GB Mavi",
        "1236631": "Realme 12 Pro 256 GB Bej",
        "1236114": "Realme 12 Lite 256 GB 8 GB Vaha Güneşi",
        "1236115": "Realme 12 Lite 256 GB 8 GB Kaya Siyahı",
        "1236116": "Realme 12 Lite 128 GB 6 GB Vaha Güneşi",
        "1236117": "Realme 12 Lite 128 GB 6 GB Kaya Siyahı",
        "1238724": "Realme 12 Plus 256 GB Bej",
        "1238582": "Realme 12 Plus 256 GB Yeşil",
        "1238583": "Realme 12 256 GB Ufuk Mavisi",
        "1238584": "Realme 12 256 GB Derin Yeşil",
        "1238585": "Realme 12 512 GB Ufuk Mavisi",
        "1238586": "Realme 12 512 GB Derin Yeşil",
    }
    if url:
        try:
            parsed = urllib.parse.urlparse(url)
            path_parts = parsed.path.split('-')
            if path_parts:
                last_part = path_parts[-1]
                product_id = last_part.replace(".html", "")
                logger.debug("adjust_realme_product_name: Tespit edilen ürün ID'si: %s", product_id)
                flush_logs()
                if product_id in realme_name_mapping:
                    correct_name = realme_name_mapping[product_id]
                    logger.info("adjust_realme_product_name: Ürün ID'si %s için adı bulundu: %s", product_id, correct_name)
                    flush_logs()
                    return correct_name
                else:
                    logger.warning("adjust_realme_product_name: Ürün ID'si %s için eşleşme bulunamadı.", product_id)
                    flush_logs()
        except Exception as e:
            logger.error("adjust_realme_product_name: URL'den ürün ID'si çıkarılırken hata: %s", e)
            flush_logs()
    return product_name

def adjust_samsung_product_name(product_name: str, url: str = None) -> str:
    """
    Verilen Samsung ürün URL'sine göre, önceden tanımlı mapping ile normalize edilmiş
    ürün adını döndürür. URL'den ürün ID'si çıkarılamazsa ya da mapping bulunamazsa genel
    düzenleme (adjust_product_name_for_akakce) uygulanır.
    """
    samsung_name_mapping = {
        "1245636": "Samsung Galaxy S25 Ultra 256 GB Titanyum Siyah",
        "1245473": "Samsung Galaxy S25 Ultra 256 GB Titanyum Gri",
        "1245472": "Samsung Galaxy S25 Ultra 256 GB Titanyum Mavi",
        "1243753": "Samsung Galaxy S25 Ultra 512 GB Titanyum Siyah",
        "1243751": "Samsung Galaxy S25 Ultra 512 GB Titanyum Mavi",
        "1243750": "Samsung Galaxy S25 Ultra 512 GB Titanyum Gümüş",
        "1243752": "Samsung Galaxy S25 Ultra 512 GB Titanyum Gri",
        "1245236": "Samsung Galaxy S25 Ultra 256 GB Titanyum Gümüş",
        "1243746": "Samsung Galaxy S25 Ultra 1 TB Titanyum Siyah",
        "1243747": "Samsung Galaxy S25 Ultra 1 TB Titanyum Mavi",
        "1243749": "Samsung Galaxy S25 Ultra 1 TB Titanyum Gümüş",
        "1243748": "Samsung Galaxy S25 Ultra 1 TB Titanyum Gri",
        "1243756": "Samsung Galaxy S25 Plus 256 GB Mint Yeşili",
        "1243761": "Samsung Galaxy S25 Plus 256 GB Gümüş",
        "1243755": "Samsung Galaxy S25 Plus 256 GB Buz Mavi",
        "1243759": "Samsung Galaxy S25 256 GB Mint Yeşili",
        "1243757": "Samsung Galaxy S25 256 GB Lacivert",
        "1243760": "Samsung Galaxy S25 256 GB Gümüş",
        "1243758": "Samsung Galaxy S25 256 GB Buz Mavi",
        "1240651": "Samsung Galaxy S24 FE 256 GB Gri",
        "1240652": "Samsung Galaxy S24 FE 256 GB Grafit",
        "1235312": "Samsung Galaxy S24 Ultra 256 GB Titanyum Siyah",
        "1235298": "Samsung Galaxy S24 Ultra 256 GB Titanyum Sarı",
        "1235297": "Samsung Galaxy S24 Ultra 256 GB Titanyum Mor",
        "1235296": "Samsung Galaxy S24 Ultra 256 GB Titanyum Gri",
        "1235286": "Samsung Galaxy S24 Plus 256 GB Sarı",
        "1235293": "Samsung Galaxy S24 Plus 256 GB Mor",
        "1235292": "Samsung Galaxy S24 Plus 256 GB Gri",
        "1232995": "Samsung Galaxy S23 FE 256 GB Siyah",
        "1245752": "Samsung Galaxy A56 256 GB Yeşil",
        "1245761": "Samsung Galaxy A56 256 GB Gri",
        "1245807": "Samsung Galaxy A56 256 GB Grafit",
        "1245768": "Samsung Galaxy A56 256 GB Pembe",
        "1245779": "Samsung Galaxy A36 256 GB Siyah",
        "1245782": "Samsung Galaxy A36 256 GB Lila",
        "1245776": "Samsung Galaxy A36 256 GB Yeşil",
        "1245781": "Samsung Galaxy A36 256 GB Gri",
        "1236154": "Samsung Galaxy A35 256 GB Mavi",
        "1245789": "Samsung Galaxy A26 256 GB 8 GB Siyah",
        "1245787": "Samsung Galaxy A26 256 GB 8 GB Pembe",
        "1245788": "Samsung Galaxy A26 256 GB 8 GB Beyaz",
        "1241462": "Samsung Galaxy A16 128 GB 6 GB Yeşil",
        "1241464": "Samsung Galaxy A16 128 GB 6 GB Siyah",
        "1241463": "Samsung Galaxy A16 128 GB 6 GB Gri",
        "1239455": "Samsung Galaxy A06 128 GB Siyah",
        "1239457": "Samsung Galaxy A06 128 GB Mavi"
    }
    if url:
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            parts = path.split('-')
            if parts:
                last_part = parts[-1]
                product_id = last_part.replace('.html', '')
                if product_id in samsung_name_mapping:
                    logger.info("adjust_samsung_product_name: Mapping bulundu, ürün ID: %s, isim: %s", product_id, samsung_name_mapping[product_id])
                    flush_logs()
                    return samsung_name_mapping[product_id]
                else:
                    logger.warning("adjust_samsung_product_name: Ürün ID: %s için mapping bulunamadı.", product_id)
                    flush_logs()
        except Exception as e:
            logger.error("adjust_samsung_product_name: URL'den ürün ID'si çıkarılırken hata: %s", e)
            flush_logs()
    logger.info("adjust_samsung_product_name: URL bilgisi mevcut değil veya mapping bulunamadı. Genel düzenleme uygulanıyor.")
    flush_logs()
    final_name = adjust_product_name_for_akakce(product_name)
    return final_name

def adjust_apple_product_name(product_name: str, url: str = None) -> str:
    """
    Verilen Apple ürün URL'sine göre, önceden tanımlı mapping ile doğru
    ürün adını döndürür. URL'den ürün ID'si çıkarılamazsa veya mapping bulunamazsa,
    orijinal product_name değeri geri döndürülür.
    """
    apple_name_mapping = {
        "1217606": "iPhone 13 128 GB Gece Yarısı",
        "1217605": "iPhone 13 128 GB Yıldız Işığı",
        "1223360": "iPhone 14 128 GB Mavi",
        "1223361": "iPhone 14 256 GB Gece Yarısı",
        "1223362": "iPhone 14 256 GB Yıldız Işığı",
        "1232436": "iPhone 15 128 GB Mavi",
        "1232438": "iPhone 15 128 GB Pembe",
        "1232435": "iPhone 15 128 GB Siyah",
        "1232441": "iPhone 15 256 GB Mavi",
        "1232443": "iPhone 15 256 GB Pembe",
        "1232444": "iPhone 15 256 GB Sarı",
        "1232440": "iPhone 15 256 GB Siyah",
        "1232442": "iPhone 15 256 GB Yeşil",
        "1232458": "iPhone 15 512 GB Pembe",
        "1232459": "iPhone 15 512 GB Sarı",
        "1232455": "iPhone 15 512 GB Siyah",
        "1232457": "iPhone 15 512 GB Yeşil",
        "1232448": "iPhone 15 Plus 128 GB Pembe",
        "1232449": "iPhone 15 Plus 128 GB Sarı",
        "1232445": "iPhone 15 Plus 128 GB Siyah",
        "1232451": "iPhone 15 Plus 256 GB Mavi",
        "1232450": "iPhone 15 Plus 256 GB Siyah",
        "1232452": "iPhone 15 Plus 256 GB Yeşil",
        "1232465": "iPhone 15 Plus 512 GB Mavi",
        "1232467": "iPhone 15 Plus 512 GB Pembe",
        "1239557": "iPhone 16 128 GB Beyaz",
        "1239560": "iPhone 16 128 GB Pembe",
        "1239553": "iPhone 16 128 GB Siyah",
        "1239565": "iPhone 16 128 GB Deniz Mavisi",
        "1239562": "iPhone 16 128 GB Laciverttaş",
        "1239570": "iPhone 16 256 GB Beyaz",
        "1239573": "iPhone 16 256 GB Pembe",
        "1239568": "iPhone 16 256 GB Siyah",
        "1239578": "iPhone 16 256 GB Deniz Mavisi",
        "1239575": "iPhone 16 256 GB Laciverttaş",
        "1239586": "iPhone 16 512 GB Beyaz",
        "1239590": "iPhone 16 512 GB Pembe",
        "1239583": "iPhone 16 512 GB Siyah",
        "1239596": "iPhone 16 512 GB Deniz Mavisi",
        "1239594": "iPhone 16 512 GB Laciverttaş",
        "1239600": "iPhone 16 Plus 128 GB Beyaz",
        "1239602": "iPhone 16 Plus 128 GB Pembe",
        "1239597": "iPhone 16 Plus 128 GB Siyah",
        "1239605": "iPhone 16 Plus 128 GB Deniz Mavisi",
        "1239604": "iPhone 16 Plus 128 GB Laciverttaş",
        "1239608": "iPhone 16 Plus 256 GB Beyaz",
        "1239610": "iPhone 16 Plus 256 GB Pembe",
        "1239606": "iPhone 16 Plus 256 GB Siyah",
        "1239612": "iPhone 16 Plus 256 GB Deniz Mavisi",
        "1239611": "iPhone 16 Plus 256 GB Laciverttaş",
        "1239554": "iPhone 16 Plus 512 GB Pembe",
        "1239551": "iPhone 16 Plus 512 GB Siyah",
        "1239556": "iPhone 16 Plus 512 GB Deniz Mavisi",
        "1239555": "iPhone 16 Plus 512 GB Laciverttaş",
        "1239559": "iPhone 16 Pro 128 GB Beyaz Titanyum",
        "1239561": "iPhone 16 Pro 128 GB Çöl Titanyum",
        "1239563": "iPhone 16 Pro 128 GB Natürel Titanyum",
        "1239558": "iPhone 16 Pro 128 GB Siyah Titanyum",
        "1239585": "iPhone 16 Pro 1 TB Natürel Titanyum",
        "1239567": "iPhone 16 Pro 256 GB Çöl Titanyum",
        "1239574": "iPhone 16 Pro 512 GB Çöl Titanyum",
        "1239577": "iPhone 16 Pro 512 GB Natürel Titanyum",
        "1239595": "iPhone 16 Pro Max 1 TB Beyaz Titanyum",
        "1239598": "iPhone 16 Pro Max 1 TB Çöl Titanyum",
        "1239599": "iPhone 16 Pro Max 1 TB Natürel Titanyum",
        "1239589": "iPhone 16 Pro Max 256 GB Beyaz Titanyum",
        "1239591": "iPhone 16 Pro Max 256 GB Çöl Titanyum",
        "1239587": "iPhone 16 Pro Max 256 GB Siyah Titanyum",
        "1239579": "iPhone 16 Pro Max 512 GB Beyaz Titanyum",
        "1239582": "iPhone 16 Pro Max 512 GB Çöl Titanyum",
        "1239588": "iPhone 16 Pro Max 512 GB Natürel Titanyum",
        "1244798": "iPhone 16e 128 GB Beyaz",
        "1244800": "iPhone 16e 128 GB Beyaz",
        "1244801": "iPhone 16e 256 GB Siyah",
        "1244802": "iPhone 16e 256 GB Beyaz",
        "1244803": "iPhone 16e 512 GB Siyah",
        "1244804": "iPhone 16e 512 GB Beyaz",
        "1239569": "iPhone 16 Pro 256 GB Natürel Titanyum",
        "1239564": "iPhone 16 Pro 256 GB Siyah Titanyum",
        "1239566": "iPhone 16 Pro 256 GB Beyaz Titanyum",
        "1239571": "iPhone 16 Pro 512 GB Siyah Titanyum",
        "1239580": "iPhone 16 Pro 1 TB Siyah Titanyum",
        "1239584": "iPhone 16 Pro 1 TB Çöl Titanyum",
        "1239581": "iPhone 16 Pro 1 TB Beyaz Titanyum",
        "1239592": "iPhone 16 Pro Max 256 GB Natürel Titanyum",
        "1239576": "iPhone 16 Pro Max 512 GB Siyah Titanyum",
        "1239593": "iPhone 16 Pro Max 1 TB Siyah Titanyum",
    }
    if url:
        try:
            parsed = urllib.parse.urlparse(url)
            path_parts = parsed.path.split('-')
            if path_parts:
                # Son parça "-<ID>.html" şeklindedir.
                last_part = path_parts[-1]
                product_id = last_part.replace(".html", "")
                logger.debug("adjust_apple_product_name: Tespit edilen ürün ID'si: %s", product_id)
                flush_logs()
                if product_id in apple_name_mapping:
                    correct_name = apple_name_mapping[product_id]
                    logger.info("adjust_apple_product_name: Ürün ID'si %s için doğru ad bulundu: %s", product_id, correct_name)
                    flush_logs()
                    return correct_name
                else:
                    logger.warning("adjust_apple_product_name: Ürün ID'si %s için eşleşme bulunamadı.", product_id)
                    flush_logs()
        except Exception as e:
            logger.error("adjust_apple_product_name: URL'den ürün ID'si çıkarılırken hata: %s", e)
            flush_logs()
    return product_name

def extract_product_name_from_url(url):
    logger.debug("extract_product_name_from_url: URL: %s", url)
    flush_logs()
    pattern_simple = re.compile(r'^(\d+)(gb|tb)$', re.IGNORECASE)
    pattern_composite_two = re.compile(r'^(\d{1,2})\s*gb\s*(\d{3})\s*gb$', re.IGNORECASE)
    pattern_composite_one = re.compile(r'^(\d{1,2})(\d{3})\s*gb$', re.IGNORECASE)
    pattern_composite_tb = re.compile(r'^(\d{1,2})(\d{1,2})\s*tb$', re.IGNORECASE)
    mapping = {
        "titanyum": "Titan",
        "gumus": "Gümüş",
        "grafit": "Grafit",
        "mor": "Mor",
        "mavi": "Mavi",
        "mavisi": "Mavi",
        "siyah": "Siyah",
        "siyahi": "Siyah",
        "beyaz": "Beyaz",
        "pembe": "Pembe",
        "yesil": "Yeşil",
        "yesili": "Yeşil",
        "sari": "Sarı",
        "kirmizi": "Kırmızı",
        "mint": "Mint",
        "lacivert": "Lacivert",
        "lila": "Lila",
        "bej": "Bej",
        "krem": "Krem",
        "turuncu": "Turuncu",
        "safir": "Safir",
        "mistik": "Mistik",
        "bronz": "Bronz",
        "acik": "Açık",
        "5g": "5G",
        "altin": "Altın"
    }
    removal_tokens = {"akilli", "telefon", "akillitelefon", "gece", "dalga", "parlak", "koyu", "yildiz", "kasif", "firtina", "gb"}
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    prefix = '/tr/product/'
    if path.startswith(prefix):
        product_part = path[len(prefix):]
    else:
        product_part = path
    product_part = product_part.lstrip('_')
    product_part = re.sub(r'\.html$', '', product_part)
    tokens = product_part.split('-')
    if tokens and tokens[-1].isdigit():
        tokens = tokens[:-1]
    lower_tokens = [t.lower() for t in tokens]
    model_series = None
    i = 0
    while i < len(tokens):
        token_upper = tokens[i].upper()
        token_lower = tokens[i].lower()
        if token_upper.startswith("S24"):
            if i + 1 < len(tokens) and tokens[i+1].lower() == "ultra":
                model_series = "S24 Ultra"
                i += 1
            else:
                model_series = "S24"
            break
        elif token_upper.startswith("S25"):
            if i + 1 < len(tokens) and tokens[i+1].lower() == "ultra":
                model_series = "S25 Ultra"
                i += 1
            elif i + 1 < len(tokens) and tokens[i+1].lower() == "plus":
                model_series = "S25 Plus"
                i += 1
            else:
                model_series = "S25"
            break
        elif token_upper.startswith("S23"):
            model_series = "S23"
            break
        elif token_upper.startswith("A06"):
            model_series = "A06"
            break
        elif token_upper.startswith("A25"):
            model_series = "A25"
            break
        elif token_upper.startswith("A56"):
            model_series = "A56"
            break
        elif token_upper.startswith("A55"):
            model_series = "A55"
            break
        elif token_upper.startswith("A36"):
            model_series = "A36"
            break
        elif token_upper.startswith("A35"):
            model_series = "A35"
            break
        elif token_lower.startswith("xiaomi") or token_lower.startswith("redmi") or token_lower.startswith("poco"):
            model_series = "Xiaomi"
            break
        elif token_lower.startswith("realme"):
            model_series = "Realme"
            break
        elif token_lower.startswith("oppo"):
            model_series = "Oppo"
            break
        elif token_lower.startswith("apple"):
            model_series = "Apple"
            break
        i += 1
    logger.debug("extract_product_name_from_url: Model serisi tespit edildi: %s", model_series)
    flush_logs()
    processed_tokens = []
    j = 0
    while j < len(tokens):
        token = tokens[j]
        token_lower = token.lower()
        if re.match(r'^rmx\d+$', token_lower):
            j += 1
            continue
        current_tokens_lower = [t.lower() for t in tokens]
        if "14t" in current_tokens_lower:
            if token_lower in {"8gb", "6gb", "16gb", "4gb"}:
                j += 1
                continue
        if token_lower in {"8gb", "6gb", "16gb", "4gb"}:
            j += 1
            continue
        if token_lower in removal_tokens:
            j += 1
            continue
        if token.isdigit() and len(token) in {4, 5}:
            if "xiaomi" in lower_tokens or "redmi" in lower_tokens:
                processed_tokens.append(process_xiaomi_capacity(token, tokens))
                j += 1
                continue
            else:
                if token.endswith("256") or token.endswith("512") or token.endswith("128"):
                    capacity = token[-3:]
                    processed_tokens.append(f"{int(capacity)} GB")
                    j += 1
                    continue
        m_comp_tb = pattern_composite_tb.match(token)
        if m_comp_tb:
            group1 = m_comp_tb.group(1)
            group2 = m_comp_tb.group(2)
            unit = "TB"
            if model_series and str(model_series).lower().startswith(("s25", "s24")):
                processed_tokens.append(f"{int(group2)} {unit}")
            else:
                processed_tokens.append(f"{int(group2)} {unit}")
                processed_tokens.append(f"{int(group1)} {unit}")
            j += 1
            continue
        m_comp = pattern_composite_two.match(token)
        if not m_comp:
            m_comp = pattern_composite_one.match(token)
        if m_comp:
            group1 = m_comp.group(1)
            group2 = m_comp.group(2)
            unit = "GB"
            if model_series == "A25":
                processed_tokens.append(f"{int(group2)} {unit}")
                processed_tokens.append(f"{int(group1)} {unit}")
            elif model_series in {"A56", "A55", "A36", "A35", "A06"} or (model_series and str(model_series).lower().startswith(("s25", "s24"))):
                processed_tokens.append(f"{int(group2)} {unit}")
            else:
                processed_tokens.append(f"{int(group2)} {unit}")
                processed_tokens.append(f"{int(group1)} {unit}")
            j += 1
            continue
        m_simple = pattern_simple.match(token)
        if m_simple:
            num = m_simple.group(1)
            unit = m_simple.group(2).upper()
            processed_tokens.append(f"{int(num)} {unit}")
            j += 1
            continue
        if token_lower in mapping:
            mapped = mapping[token_lower]
            if mapped == "":
                j += 1
                continue
            processed_tokens.append(mapped)
        else:
            if token_lower[0].isalpha() and any(ch.isdigit() for ch in token_lower):
                processed_tokens.append(token.upper())
            else:
                processed_tokens.append(token.capitalize())
        j += 1
    raw_name = " ".join(processed_tokens)
    logger.debug("extract_product_name_from_url: İşlenmiş ham ürün ismi: %s", raw_name)
    flush_logs()
    try:
        final_name = adjust_product_name_for_akakce(raw_name)
        logger.debug("extract_product_name_from_url: Nihai ürün ismi: %s", final_name)
    except Exception as e:
        logger.error("extract_product_name_from_url: İsim düzenleme hatası: %s", e)
        final_name = raw_name
    flush_logs()
    
    if model_series == "Oppo" or ("oppo" in url.lower() if url else False):
        final_name = adjust_oppo_product_name(final_name, url)
    if "14t" in [t.lower() for t in tokens]:
        final_name = re.sub(r'(?i)\b14t\b', "14T", final_name)
        final_name = re.sub(r'(?i)\bsiyah\b', "Titan Siyahı", final_name)
        final_name = re.sub(r'(?i)\bmavi\b', "Titan Mavisi", final_name)
        final_name = re.sub(r'(?i)\bgri\b', "Titan Grisi", final_name)
    if model_series == "Realme" or ("realme" in url.lower() if url else False):
        final_name = adjust_realme_product_name(final_name, url)
    if model_series == "Xiaomi" or ("xiaomi" in url.lower() or "redmi" in url.lower() or "poco" in url.lower() if url else False):
        final_name = adjust_xiaomi_product_name(final_name, url)
    if model_series == "Samsung" or ("samsung" in url.lower() if url else False):
        final_name = adjust_samsung_product_name(final_name, url)
    if model_series == "Apple" or ("apple" in url.lower() if url else False):
        final_name = adjust_apple_product_name(final_name, url)
    if "14c" in [t.lower() for t in tokens]:
        final_name = re.sub(r'(?i)\b14c\b', "14C", final_name)
    return final_name

def clean_price(price_str):
    logger.debug("clean_price: Girdi: %s", price_str)
    flush_logs()
    cleaned_price = price_str.replace(' TL', '').replace(' ', '').replace('\u20ba', '').replace('–', '')
    cleaned_price = cleaned_price.replace('.', '').replace(',', '.')
    try:
        price = float(cleaned_price)
        logger.debug("clean_price: Dönüştürülmüş fiyat: %f", price)
    except Exception as e:
        logger.error("clean_price: Fiyat dönüştürme hatası: %s", e)
        price = 0.0
    flush_logs()
    return price, None

def format_price_to_user_friendly(price_float):
    logger.debug("format_price_to_user_friendly: Girdi: %f", price_float)
    flush_logs()
    formatted_price = "{:,.2f}".format(price_float)\
        .replace(",", "TEMP")\
        .replace(".", ",")\
        .replace("TEMP", ".")
    result = formatted_price + " TL"
    logger.debug("format_price_to_user_friendly: Çıktı: %s", result)
    flush_logs()
    return result
