import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
import random
from datetime import datetime
import json
from textblob import TextBlob
import io

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Extracteur d'avis Amazon - Batch",
    page_icon="📝",
    layout="wide"
)

class SentimentAnalyzer:
    """Analyseur de sentiment pour les commentaires"""
    
    @staticmethod
    def analyze_sentiment(text):
        """Analyse le sentiment d'un texte et retourne un label"""
        if not text or len(text.strip()) < 3:
            return "Neutre"
        
        try:
            # Utilisation de TextBlob pour l'analyse de sentiment
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return "Positif"
            elif polarity < -0.1:
                return "Négatif"
            else:
                return "Neutre"
        except:
            return "Neutre"

class AmazonReviewsExtractor:
    def __init__(self):
        # Headers plus réalistes pour éviter la détection
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
    def clean_url(self, url):
        """Nettoie l'URL pour extraire l'URL de base du produit"""
        try:
            # Extraire l'ASIN de différents formats d'URL
            patterns = [
                r'/dp/([A-Z0-9]{10})',
                r'/product/([A-Z0-9]{10})',
                r'asin=([A-Z0-9]{10})',
                r'/gp/product/([A-Z0-9]{10})',
                r'/([A-Z0-9]{10})(?:/|$)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    asin = match.group(1)
                    # Détecter le domaine Amazon
                    if "amazon.fr" in url:
                        return f"https://www.amazon.fr/dp/{asin}", asin
                    elif "amazon.com" in url:
                        return f"https://www.amazon.com/dp/{asin}", asin
                    elif "amazon.de" in url:
                        return f"https://www.amazon.de/dp/{asin}", asin
                    elif "amazon.co.uk" in url:
                        return f"https://www.amazon.co.uk/dp/{asin}", asin
                    else:
                        # Par défaut, amazon.fr
                        return f"https://www.amazon.fr/dp/{asin}", asin
            
            return None, None
        except Exception as e:
            st.error(f"Erreur lors du nettoyage de l'URL: {str(e)}")
            return None, None
    
    def get_reviews_url(self, product_url, asin):
        """Construit l'URL de la page des avis"""
        try:
            if "amazon.fr" in product_url:
                return f"https://www.amazon.fr/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber=1"
            elif "amazon.com" in product_url:
                return f"https://www.amazon.com/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber=1"
            elif "amazon.de" in product_url:
                return f"https://www.amazon.de/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber=1"
            elif "amazon.co.uk" in product_url:
                return f"https://www.amazon.co.uk/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber=1"
            else:
                return f"https://www.amazon.fr/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber=1"
        except:
            return None
    
    def extract_product_info(self, product_url):
        """Extrait les informations générales du produit"""
        try:
            st.write(f"🔍 Extraction des infos produit depuis: {product_url}")
            
            # Pause aléatoire
            time.sleep(random.uniform(2, 5))
            
            session = requests.Session()
            session.headers.update(self.headers)
            
            response = session.get(product_url, timeout=15)
            
            if response.status_code != 200:
                st.warning(f"⚠️ Code HTTP {response.status_code} pour la page produit")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multiples sélecteurs pour la note moyenne (Amazon change souvent)
            avg_rating = None
            rating_selectors = [
                'span.a-icon-alt',
                'span[data-hook="rating-out-of-text"]',
                'span.a-offscreen',
                'i.a-icon-star span.a-offscreen',
                '.a-icon-star .a-offscreen'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = soup.select_one(selector)
                    if rating_elem:
                        rating_text = rating_elem.text or rating_elem.get('title', '')
                        rating_match = re.search(r'(\d+(?:[,\.]\d+)?)', rating_text)
                        if rating_match:
                            avg_rating = float(rating_match.group(1).replace(',', '.'))
                            break
                except:
                    continue
            
            # Multiples sélecteurs pour le nombre total d'avis
            total_reviews = 0
            review_count_selectors = [
                'span[data-hook="total-review-count"]',
                'a[data-hook="see-all-reviews-link-foot"]',
                '#acrCustomerReviewText',
                'span#acrCustomerReviewText',
                '.a-link-normal[data-hook="see-all-reviews-link-foot"]'
            ]
            
            for selector in review_count_selectors:
                try:
                    reviews_elem = soup.select_one(selector)
                    if reviews_elem:
                        reviews_text = reviews_elem.text
                        # Recherche de nombres dans le texte
                        numbers = re.findall(r'(\d+(?:[\s,]\d+)*)', reviews_text.replace(',', '').replace(' ', ''))
                        if numbers:
                            total_reviews = int(numbers[0])
                            break
                except:
                    continue
            
            st.success(f"✅ Info produit: {avg_rating}/5 ⭐ | {total_reviews} avis")
            
            return {
                'avg_rating': avg_rating,
                'total_reviews': total_reviews
            }
            
        except Exception as e:
            st.warning(f"⚠️ Erreur lors de l'extraction des infos produit: {str(e)}")
            return None
    
    def extract_single_review(self, review_element):
        """Extrait les informations d'un seul avis"""
        try:
            review_data = {}
            
            # Multiples sélecteurs pour la note
            rating = None
            rating_selectors = [
                'span.a-icon-alt',
                'i.a-icon-star span.a-offscreen',
                '.a-icon-star .a-offscreen',
                'span[data-hook="review-star-rating"] span.a-offscreen'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = review_element.select_one(selector)
                    if rating_elem:
                        rating_text = rating_elem.text or rating_elem.get('title', '')
                        rating_match = re.search(r'(\d+(?:[,\.]\d+)?)', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1).replace(',', '.'))
                            break
                except:
                    continue
            
            review_data['rating'] = rating
            
            # Multiples sélecteurs pour le contenu
            content = ""
            content_selectors = [
                'span[data-hook="review-body"]',
                '.review-text',
                '.cr-original-review-text',
                'div[data-hook="review-body"] span'
            ]
            
            for selector in content_selectors:
                try:
                    content_elem = review_element.select_one(selector)
                    if content_elem:
                        content = content_elem.get_text(strip=True)
                        if content and len(content) > 10:  # Au moins 10 caractères
                            break
                except:
                    continue
            
            review_data['content'] = content
            
            return review_data if (rating is not None or content) else None
            
        except Exception as e:
            return None
    
    def extract_reviews_for_product(self, original_url, max_pages=3):
        """Extrait les avis d'un produit spécifique"""
        try:
            # Nettoyer l'URL
            clean_url, asin = self.clean_url(original_url)
            
            if not clean_url or not asin:
                st.error(f"❌ Impossible d'extraire l'ASIN depuis: {original_url}")
                return None
            
            st.info(f"🧹 URL nettoyée: {clean_url}")
            st.info(f"🆔 ASIN détecté: {asin}")
            
            # Extraction des informations générales du produit
            product_info = self.extract_product_info(clean_url)
            
            # URL des avis
            reviews_url = self.get_reviews_url(clean_url, asin)
            if not reviews_url:
                st.error("❌ Impossible de construire l'URL des avis")
                return None
            
            st.info(f"📄 URL des avis: {reviews_url}")
            
            reviews = []
            session = requests.Session()
            session.headers.update(self.headers)
            
            # Extraction des avis détaillés
            for page in range(1, max_pages + 1):
                try:
                    st.write(f"📖 Extraction page {page}/{max_pages}...")
                    
                    current_url = reviews_url.replace('pageNumber=1', f'pageNumber={page}')
                    time.sleep(random.uniform(3, 6))  # Pause plus longue
                    
                    response = session.get(current_url, timeout=15)
                    
                    if response.status_code != 200:
                        st.warning(f"⚠️ Code HTTP {response.status_code} pour la page {page}")
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Multiples sélecteurs pour les avis
                    review_selectors = [
                        'div[data-hook="review"]',
                        '.review',
                        '.cr-original-review-text',
                        'div.a-section.review'
                    ]
                    
                    review_elements = []
                    for selector in review_selectors:
                        elements = soup.select(selector)
                        if elements:
                            review_elements = elements
                            break
                    
                    if not review_elements:
                        st.warning(f"⚠️ Aucun avis trouvé sur la page {page}")
                        # Essayer avec d'autres sélecteurs
                        all_divs = soup.find_all('div', class_=True)
                        review_elements = [div for div in all_divs if 'review' in ' '.join(div.get('class', [])).lower()]
                    
                    if not review_elements:
                        st.warning(f"⚠️ Aucune structure d'avis détectée page {page}")
                        break
                    
                    page_reviews = 0
                    for review_element in review_elements:
                        review_data = self.extract_single_review(review_element)
                        if review_data and review_data.get('content'):
                            reviews.append(review_data)
                            page_reviews += 1
                    
                    st.success(f"✅ Page {page}: {page_reviews} avis extraits")
                    
                    if page_reviews == 0:
                        st.warning("⚠️ Aucun avis avec contenu trouvé, arrêt de l'extraction")
                        break
                    
                    # Vérifier s'il y a une page suivante
                    next_disabled = soup.select_one('li.a-disabled.a-last')
                    if next_disabled:
                        st.info("📄 Dernière page atteinte")
                        break
                        
                except Exception as e:
                    st.error(f"❌ Erreur page {page}: {str(e)}")
                    continue
            
            return {
                'product_info': product_info,
                'reviews': reviews,
                'asin': asin,
                'clean_url': clean_url
            }
            
        except Exception as e:
            st.error(f"❌ Erreur générale pour {original_url}: {str(e)}")
            return None

def process_batch_urls(urls, max_pages_per_product=3, progress_placeholder=None):
    """Traite une liste d'URLs en batch"""
    extractor = AmazonReviewsExtractor()
    analyzer = SentimentAnalyzer()
    results = []
    
    total_urls = len(urls)
    
    for i, url in enumerate(urls):
        if progress_placeholder:
            progress_placeholder.progress((i + 1) / total_urls)
            
        st.subheader(f"🔄 URL {i+1}/{total_urls}")
        st.write(f"**URL originale:** {url}")
        
        # Extraction des données pour ce produit
        product_data = extractor.extract_reviews_for_product(url.strip(), max_pages_per_product)
        
        if product_data and product_data['reviews']:
            product_info = product_data['product_info'] or {}
            reviews = product_data['reviews']
            
            # Calcul des statistiques
            total_reviews = product_info.get('total_reviews', len(reviews))
            avg_rating = product_info.get('avg_rating')
            if not avg_rating and reviews:
                # Calcul de la moyenne sur les avis extraits
                ratings = [r['rating'] for r in reviews if r['rating'] is not None]
                avg_rating = sum(ratings) / len(ratings) if ratings else None
            
            # Création d'une ligne par avis
            for review in reviews:
                if review.get('content'):  # Seulement les avis avec commentaire
                    sentiment = analyzer.analyze_sentiment(review['content'])
                    
                    results.append({
                        'url': url.strip(),
                        'nombre_avis': total_reviews,
                        'nombre_commentaires_client': len(reviews),
                        'moyenne_avis': round(avg_rating, 1) if avg_rating else None,
                        'avis_notation': review.get('rating'),
                        'commentaire_associe': review['content'],
                        'sentiment': sentiment
                    })
            
            st.success(f"✅ **Résultat:** {len(reviews)} avis extraits avec succès!")
        else:
            st.error(f"❌ **Échec:** Aucun avis extrait pour cette URL")
            # Ajouter une ligne vide pour cette URL
            results.append({
                'url': url.strip(),
                'nombre_avis': 0,
                'nombre_commentaires_client': 0,
                'moyenne_avis': None,
                'avis_notation': None,
                'commentaire_associe': "Aucun avis extrait",
                'sentiment': "N/A"
            })
        
        st.markdown("---")
    
    return results

def main():
    st.title("📝 Extracteur d'avis Amazon - Version Améliorée")
    st.markdown("---")
    
    # Avertissement légal
    with st.expander("⚠️ Avertissement important", expanded=True):
        st.warning("""
        **Utilisation responsable uniquement:**
        - Cet outil est destiné à un usage éducatif et de recherche
        - Respectez les conditions d'utilisation d'Amazon
        - Le traitement peut prendre beaucoup de temps (pauses anti-détection)
        - Amazon peut bloquer les requêtes automatisées
        - Testez d'abord avec une seule URL
        """)
    
    # Mode de test pour debug
    st.sidebar.header("🛠️ Mode Debug")
    debug_mode = st.sidebar.checkbox("Activer le mode debug (plus de logs)")
    
    # Choix du mode
    mode = st.radio(
        "🎯 Mode d'extraction:",
        ["URL unique (recommandé pour test)", "Traitement en batch"],
        horizontal=True
    )
    
    if mode == "URL unique (recommandé pour test)":
        st.subheader("🧪 Test avec une URL unique")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            product_url = st.text_input(
                "🔗 URL du produit Amazon:",
                placeholder="https://www.amazon.fr/dp/XXXXXXXXXX",
                help="Testez d'abord avec une URL pour vérifier que l'extraction fonctionne"
            )
        
        with col2:
            max_pages = st.number_input(
                "📄 Nombre de pages max:",
                min_value=1,
                max_value=5,
                value=2,
                help="Commencez avec 1-2 pages pour tester"
            )
        
        if st.button("🚀 Tester l'extraction", type="primary"):
            if product_url:
                with st.container():
                    st.info("🔄 **Début de l'extraction de test...**")
                    
                    urls = [product_url]
                    progress_bar = st.progress(0)
                    results = process_batch_urls(urls, max_pages, progress_bar)
                    
                    if results and any(r['commentaire_associe'] != "Aucun avis extrait" for r in results):
                        df = pd.DataFrame(results)
                        
                        st.success(f"🎉 **Test réussi!** {len([r for r in results if r['commentaire_associe'] != 'Aucun avis extrait'])} avis extraits!")
                        
                        # Aperçu des résultats
                        st.subheader("📊 Aperçu des résultats")
                        st.dataframe(df.head(3), use_container_width=True)
                        
                        # Téléchargement CSV
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="💾 Télécharger CSV de test",
                            data=csv,
                            file_name=f"test_avis_amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("❌ **Test échoué** - Aucun avis n'a pu être extrait")
                        st.info("""
                        **Causes possibles:**
                        - L'URL n'est pas valide ou ne contient pas d'avis
                        - Amazon bloque les requêtes automatisées
                        - La structure HTML a changé
                        - Le produit n'a pas d'avis clients
                        
                        **Solutions:**
                        - Vérifiez que l'URL fonctionne dans votre navigateur
                        - Essayez avec une autre URL de produit
                        - Attendez quelques minutes et réessayez
                        """)
            else:
                st.error("❌ Veuillez saisir une URL")
    
    else:
        # Mode batch
        st.subheader("📋 Traitement en batch")
        st.warning("⚠️ **Recommandation:** Testez d'abord avec le mode 'URL unique' avant d'utiliser le batch")
        
        # Options de saisie
        input_method = st.radio(
            "Mode de saisie des URLs:",
            ["Saisie manuelle", "Upload fichier texte"],
            horizontal=True
        )
        
        urls = []
        
        if input_method == "Saisie manuelle":
            urls_text = st.text_area(
                "🔗 URLs des produits Amazon (une par ligne):",
                placeholder="https://www.amazon.fr/dp/XXXXXXXXXX\nhttps://www.amazon.fr/dp/YYYYYYYYYY\n...",
                height=150
            )
            if urls_text:
                urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        else:
            uploaded_file = st.file_uploader(
                "📁 Fichier texte avec les URLs (une par ligne)",
                type=['txt']
            )
            if uploaded_file:
                content = uploaded_file.read().decode('utf-8')
                urls = [url.strip() for url in content.split('\n') if url.strip()]
        
        if urls:
            st.info(f"📊 {len(urls)} URLs détectées")
            
            # Options pour le batch
            col1, col2 = st.columns(2)
            with col1:
                max_pages_batch = st.number_input(
                    "📄 Pages max par produit:",
                    min_value=1,
                    max_value=3,
                    value=1,
                    help="RECOMMANDÉ: 1 page pour éviter les blocages"
                )
            
            with col2:
                sample_urls = st.number_input(
                    "🎯 Limiter à N URLs (0 = toutes):",
                    min_value=0,
                    max_value=len(urls),
                    value=min(5, len(urls)),
                    help="RECOMMANDÉ: Commencez avec 5 URLs max"
                )
            
            # Aperçu des URLs
            with st.expander("👀 Aperçu des URLs à traiter"):
                display_urls = urls[:sample_urls] if sample_urls > 0 else urls
                for i, url in enumerate(display_urls, 1):
                    st.write(f"{i}. {url}")
                if sample_urls > 0 and sample_urls < len(urls):
                    st.write(f"... et {len(urls) - sample_urls} autres URLs")
            
            # Estimation du temps
            urls_to_process = sample_urls if sample_urls > 0 else len(urls)
            estimated_time = urls_to_process * max_pages_batch * 15  # ~15 sec par page avec pauses
            st.warning(f"⏱️ **Temps estimé:** ~{estimated_time//60} minutes {estimated_time%60} secondes")
            st.info("💡 Le processus peut être interrompu à tout moment avec Ctrl+C")
            
            if st.button("🚀 Lancer l'extraction en batch", type="primary"):
                if sample_urls > 0:
                    urls = urls[:sample_urls]
                
                st.warning("🕐 **Extraction en cours...** Cela peut prendre plusieurs minutes")
                
                progress_bar = st.progress(0)
                results = process_batch_urls(urls, max_pages_batch, progress_bar)
                
                if results:
                    df = pd.DataFrame(results)
                    
                    # Filtrer les résultats réussis
                    successful_results = df[df['commentaire_associe'] != 'Aucun avis extrait']
                    
                    # Statistiques globales
                    st.subheader("📊 Résultats du traitement batch")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("URLs traitées", len(df['url'].unique()))
                    with col2:
                        st.metric("URLs réussies", len(successful_results['url'].unique()))
                    with col3:
                        st.metric("Total avis", len(successful_results))
                    with col4:
                        if len(successful_results) > 0:
                            avg_rating = successful_results['avis_notation'].mean()
                            st.metric("Note moyenne", f"{avg_rating:.1f}/5" if pd.notna(avg_rating) else "N/A")
                        else:
                            st.metric("Note moyenne", "N/A")
                    
                    # Répartition des sentiments
                    if len(successful_results) > 0:
                        st.subheader("📈 Répartition des sentiments")
                        sentiment_counts = successful_results['sentiment'].value_counts()
                        st.bar_chart(sentiment_counts)
                    
                    # Affichage des données
                    st.subheader("📋 Données extraites")
                    st.dataframe(df, use_container_width=True)
                    
                    # Téléchargement
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="💾 Télécharger CSV complet",
                        data=csv,
                        file_name=f"avis_amazon_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    if len(successful_results) > 0:
                        st.success(f"✅ **Traitement terminé!** {len(successful_results)} avis extraits sur {len(urls)} URLs")
                    else:
                        st.error("❌ **Aucun avis extrait** - Toutes les URLs ont échoué")
                else:
                    st.error("❌ Aucun résultat obtenu")

    # Instructions
    with st.expander("📖 Format de sortie CSV"):
        st.markdown("""
        **Colonnes du fichier CSV exporté:**
        - `url`: URL du produit Amazon
        - `nombre_avis`: Nombre total d'avis pour ce produit
        - `nombre_commentaires_client`: Nombre de commentaires extraits
        - `moyenne_avis`: Note moyenne du produit (sur 5)
        - `avis_notation`: Note de cet avis spécifique (1-5 étoiles)
        - `commentaire_associe`: Texte du commentaire client
        - `sentiment`: Analyse de sentiment (Positif/Négatif/Neutre)
        
        **Note:** Il y a une ligne par avis/commentaire extrait.
        """)
    
    with st.expander("🔧 Installation et utilisation"):
        st.markdown("""
        **Installation:**
        ```bash
        pip install -r requirements.txt
        python -m textblob.download_corpora
        streamlit run amazon_reviews_extractor.py
        ```
        
        **Conseils d'utilisation:**
        - Commencez toujours par tester une URL unique
        - Utilisez des pauses entre les extractions batch
        - Limitez le nombre de pages pour éviter les blocages
        - Si vous êtes bloqué, attendez quelques heures avant de réessayer
        """)

if __name__ == "__main__":
    main()
