import streamlit as st
import pandas as pd
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Any
import io

def extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """Extrait les données JSON-LD du HTML"""
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    json_ld_data = []
    
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string or '')
            if isinstance(data, list):
                json_ld_data.extend(data)
            else:
                json_ld_data.append(data)
        except (json.JSONDecodeError, AttributeError):
            continue
    
    return json_ld_data

def extract_microdata(soup: BeautifulSoup) -> List[Dict]:
    """Extrait les microdonnées du HTML"""
    microdata = []
    items = soup.find_all(attrs={'itemscope': True})
    
    for item in items:
        item_data = {}
        item_type = item.get('itemtype', '')
        if item_type:
            item_data['@type'] = item_type.split('/')[-1]
        
        properties = item.find_all(attrs={'itemprop': True})
        for prop in properties:
            prop_name = prop.get('itemprop')
            prop_value = prop.get('content') or prop.get_text(strip=True)
            if prop_name and prop_value:
                item_data[prop_name] = prop_value
        
        if item_data:
            microdata.append(item_data)
    
    return microdata

def extract_open_graph(soup: BeautifulSoup) -> Dict:
    """Extrait les métadonnées Open Graph"""
    og_data = {}
    og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
    
    for tag in og_tags:
        property_name = tag.get('property', '').replace('og:', '')
        content = tag.get('content', '')
        if property_name and content:
            og_data[property_name] = content
    
    return {'@type': 'OpenGraph', **og_data} if og_data else {}

def extract_twitter_cards(soup: BeautifulSoup) -> Dict:
    """Extrait les métadonnées Twitter Cards"""
    twitter_data = {}
    twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
    
    for tag in twitter_tags:
        name = tag.get('name', '').replace('twitter:', '')
        content = tag.get('content', '')
        if name and content:
            twitter_data[name] = content
    
    return {'@type': 'TwitterCard', **twitter_data} if twitter_data else {}

def extract_meta_tags(soup: BeautifulSoup) -> Dict:
    """Extrait les métadonnées importantes"""
    meta_data = {}
    
    # Description
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    if desc_tag:
        meta_data['description'] = desc_tag.get('content', '')
    
    # Keywords
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_tag:
        meta_data['keywords'] = keywords_tag.get('content', '')
    
    # Title
    title_tag = soup.find('title')
    if title_tag:
        meta_data['title'] = title_tag.get_text(strip=True)
    
    return {'@type': 'MetaTags', **meta_data} if meta_data else {}

def extract_structured_data(html_content: str) -> Dict[str, List[Dict]]:
    """Extrait toutes les données structurées du HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    structured_data = {
        'JSON-LD': extract_json_ld(soup),
        'Microdata': extract_microdata(soup),
        'OpenGraph': [extract_open_graph(soup)] if extract_open_graph(soup) else [],
        'TwitterCards': [extract_twitter_cards(soup)] if extract_twitter_cards(soup) else [],
        'MetaTags': [extract_meta_tags(soup)] if extract_meta_tags(soup) else []
    }
    
    # Supprimer les catégories vides
    structured_data = {k: v for k, v in structured_data.items() if v}
    
    return structured_data

def get_data_types_set(structured_data: Dict[str, List[Dict]]) -> Set[str]:
    """Récupère l'ensemble des types de données présents"""
    types_set = set()
    
    for category, data_list in structured_data.items():
        for data in data_list:
            if '@type' in data:
                data_type = data['@type']
                if isinstance(data_type, list):
                    types_set.update(data_type)
                else:
                    types_set.add(data_type)
            else:
                types_set.add(category)
    
    return types_set

def flatten_data_for_comparison(structured_data: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Aplatit les données pour faciliter la comparaison"""
    flattened = {}
    
    for category, data_list in structured_data.items():
        for i, data in enumerate(data_list):
            data_type = data.get('@type', category)
            if isinstance(data_type, list):
                data_type = ', '.join(data_type)
            
            key = f"{data_type}_{i}" if len(data_list) > 1 else data_type
            flattened[key] = data
    
    return flattened

def get_schema_org_example(data_type: str) -> str:
    """Retourne un exemple de code JSON-LD selon schema.org pour un type donné"""
    examples = {
        # Thing - Base class
        'Thing': {
            "@context": "https://schema.org",
            "@type": "Thing",
            "name": "Nom de l'élément",
            "description": "Description de l'élément",
            "url": "https://www.example.com",
            "image": "https://www.example.com/image.jpg"
        },
        
        # Action types
        'Action': {
            "@context": "https://schema.org",
            "@type": "Action",
            "name": "Action générique",
            "agent": {
                "@type": "Person",
                "name": "Agent de l'action"
            },
            "startTime": "2024-01-01T10:00:00"
        },
        'ConsumeAction': {
            "@context": "https://schema.org",
            "@type": "ConsumeAction",
            "agent": {
                "@type": "Person",
                "name": "Consommateur"
            },
            "object": {
                "@type": "Product",
                "name": "Produit consommé"
            }
        },
        'WatchAction': {
            "@context": "https://schema.org",
            "@type": "WatchAction",
            "agent": {
                "@type": "Person",
                "name": "Spectateur"
            },
            "object": {
                "@type": "Movie",
                "name": "Film regardé"
            }
        },
        'ReadAction': {
            "@context": "https://schema.org",
            "@type": "ReadAction",
            "agent": {
                "@type": "Person",
                "name": "Lecteur"
            },
            "object": {
                "@type": "Article",
                "name": "Article lu"
            }
        },
        'BuyAction': {
            "@context": "https://schema.org",
            "@type": "BuyAction",
            "agent": {
                "@type": "Person",
                "name": "Acheteur"
            },
            "object": {
                "@type": "Product",
                "name": "Produit acheté"
            },
            "price": "99.99",
            "priceCurrency": "EUR"
        },
        'SearchAction': {
            "@context": "https://schema.org",
            "@type": "SearchAction",
            "target": "https://www.example.com/search?q={search_term_string}",
            "query-input": "required name=search_term_string"
        },
        'ReviewAction': {
            "@context": "https://schema.org",
            "@type": "ReviewAction",
            "agent": {
                "@type": "Person",
                "name": "Reviewer"
            },
            "object": {
                "@type": "Product",
                "name": "Produit évalué"
            },
            "result": {
                "@type": "Review",
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": "5"
                }
            }
        },
        'ShareAction': {
            "@context": "https://schema.org",
            "@type": "ShareAction",
            "agent": {
                "@type": "Person",
                "name": "Partageur"
            },
            "object": {
                "@type": "Article",
                "name": "Article partagé"
            }
        },
        
        # CreativeWork types
        'CreativeWork': {
            "@context": "https://schema.org",
            "@type": "CreativeWork",
            "name": "Œuvre créative",
            "author": {
                "@type": "Person",
                "name": "Auteur"
            },
            "datePublished": "2024-01-01"
        },
        'Article': {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Titre de l'article",
            "author": {
                "@type": "Person",
                "name": "Nom de l'auteur"
            },
            "datePublished": "2024-01-01",
            "dateModified": "2024-01-01",
            "image": "https://www.example.com/article-image.jpg",
            "publisher": {
                "@type": "Organization",
                "name": "Nom du site",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://www.example.com/logo.png"
                }
            }
        },
        'BlogPosting': {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": "Titre du blog post",
            "author": {
                "@type": "Person",
                "name": "Nom de l'auteur"
            },
            "datePublished": "2024-01-01",
            "image": "https://www.example.com/blog-image.jpg",
            "wordCount": 1500
        },
        'NewsArticle': {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": "Titre de l'actualité",
            "author": {
                "@type": "Person",
                "name": "Journaliste"
            },
            "datePublished": "2024-01-01",
            "image": "https://www.example.com/news.jpg",
            "publisher": {
                "@type": "Organization",
                "name": "Média"
            }
        },
        'Recipe': {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Nom de la recette",
            "author": {
                "@type": "Person",
                "name": "Chef"
            },
            "cookTime": "PT30M",
            "prepTime": "PT15M",
            "recipeYield": "4 portions",
            "recipeIngredient": ["Ingrédient 1", "Ingrédient 2"],
            "recipeInstructions": [
                {
                    "@type": "HowToStep",
                    "text": "Étape 1 de la recette"
                }
            ],
            "nutrition": {
                "@type": "NutritionInformation",
                "calories": "300 calories"
            }
        },
        'Book': {
            "@context": "https://schema.org",
            "@type": "Book",
            "name": "Titre du livre",
            "author": {
                "@type": "Person",
                "name": "Auteur"
            },
            "isbn": "978-0123456789",
            "genre": "Fiction",
            "publisher": {
                "@type": "Organization",
                "name": "Maison d'édition"
            },
            "datePublished": "2024-01-01"
        },
        'Movie': {
            "@context": "https://schema.org",
            "@type": "Movie",
            "name": "Titre du film",
            "director": {
                "@type": "Person",
                "name": "Réalisateur"
            },
            "actor": [
                {
                    "@type": "Person",
                    "name": "Acteur principal"
                }
            ],
            "datePublished": "2024-01-01",
            "duration": "PT120M"
        },
        'VideoObject': {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": "Titre de la vidéo",
            "description": "Description de la vidéo",
            "uploadDate": "2024-01-01",
            "contentUrl": "https://www.example.com/video.mp4",
            "thumbnailUrl": "https://www.example.com/thumbnail.jpg",
            "duration": "PT10M"
        },
        'AudioObject': {
            "@context": "https://schema.org",
            "@type": "AudioObject",
            "name": "Titre de l'audio",
            "description": "Description de l'audio",
            "contentUrl": "https://www.example.com/audio.mp3",
            "duration": "PT5M"
        },
        'ImageObject': {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "name": "Titre de l'image",
            "description": "Description de l'image",
            "contentUrl": "https://www.example.com/image.jpg",
            "width": "1920",
            "height": "1080"
        },
        'Course': {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": "Nom du cours",
            "description": "Description du cours",
            "provider": {
                "@type": "Organization",
                "name": "Organisme de formation"
            },
            "courseCode": "COURS101",
            "educationalLevel": "Débutant"
        },
        'Dataset': {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Nom du jeu de données",
            "description": "Description du dataset",
            "creator": {
                "@type": "Organization",
                "name": "Créateur"
            },
            "dateModified": "2024-01-01",
            "license": "https://creativecommons.org/licenses/by/4.0/"
        },
        'WebSite': {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Nom du site",
            "url": "https://www.example.com",
            "potentialAction": {
                "@type": "SearchAction",
                "target": "https://www.example.com/search?q={search_term_string}",
                "query-input": "required name=search_term_string"
            }
        },
        'WebPage': {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Titre de la page",
            "url": "https://www.example.com/page",
            "description": "Description de la page",
            "isPartOf": {
                "@type": "WebSite",
                "name": "Nom du site"
            }
        },
        'SoftwareApplication': {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "Nom de l'application",
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Windows, macOS, Linux",
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "EUR"
            }
        },
        'TVSeries': {
            "@context": "https://schema.org",
            "@type": "TVSeries",
            "name": "Nom de la série",
            "numberOfSeasons": "5",
            "numberOfEpisodes": "100",
            "genre": "Drame"
        },
        'Podcast': {
            "@context": "https://schema.org",
            "@type": "Podcast",
            "name": "Nom du podcast",
            "description": "Description du podcast",
            "author": {
                "@type": "Person",
                "name": "Créateur"
            }
        },
        
        # Event types
        'Event': {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Nom de l'événement",
            "startDate": "2024-07-01T19:00:00+02:00",
            "endDate": "2024-07-01T22:00:00+02:00",
            "location": {
                "@type": "Place",
                "name": "Lieu de l'événement",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "123 Rue Example",
                    "addressLocality": "Paris",
                    "postalCode": "75001",
                    "addressCountry": "FR"
                }
            },
            "organizer": {
                "@type": "Organization",
                "name": "Organisateur"
            }
        },
        'MusicEvent': {
            "@context": "https://schema.org",
            "@type": "MusicEvent",
            "name": "Concert",
            "startDate": "2024-07-01T20:00:00+02:00",
            "performer": {
                "@type": "MusicGroup",
                "name": "Nom du groupe"
            },
            "location": {
                "@type": "MusicVenue",
                "name": "Salle de concert"
            }
        },
        'SportsEvent': {
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            "name": "Match de football",
            "startDate": "2024-07-01T15:00:00+02:00",
            "competitor": [
                {
                    "@type": "SportsTeam",
                    "name": "Équipe A"
                },
                {
                    "@type": "SportsTeam",
                    "name": "Équipe B"
                }
            ]
        },
        'BusinessEvent': {
            "@context": "https://schema.org",
            "@type": "BusinessEvent",
            "name": "Conférence d'affaires",
            "startDate": "2024-07-01T09:00:00+02:00",
            "organizer": {
                "@type": "Organization",
                "name": "Organisateur professionnel"
            }
        },
        'TheaterEvent': {
            "@context": "https://schema.org",
            "@type": "TheaterEvent",
            "name": "Pièce de théâtre",
            "startDate": "2024-07-01T20:00:00+02:00",
            "performer": {
                "@type": "Person",
                "name": "Acteur principal"
            }
        },
        'Festival': {
            "@context": "https://schema.org",
            "@type": "Festival",
            "name": "Festival de musique",
            "startDate": "2024-07-01",
            "endDate": "2024-07-03",
            "location": {
                "@type": "Place",
                "name": "Parc du festival"
            }
        },
        
        # Organization types
        'Organization': {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Nom de votre organisation",
            "url": "https://www.example.com",
            "logo": "https://www.example.com/logo.png",
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+33-1-23-45-67-89",
                "contactType": "customer service"
            },
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'LocalBusiness': {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "Nom de votre entreprise",
            "image": "https://www.example.com/photo.jpg",
            "telephone": "+33-1-23-45-67-89",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "opens": "09:00",
                    "closes": "18:00"
                }
            ]
        },
        'Restaurant': {
            "@context": "https://schema.org",
            "@type": "Restaurant",
            "name": "Nom du restaurant",
            "image": "https://www.example.com/restaurant.jpg",
            "telephone": "+33-1-23-45-67-89",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "servesCuisine": "Française",
            "priceRange": "€€",
            "menu": "https://www.example.com/menu"
        },
        'Store': {
            "@context": "https://schema.org",
            "@type": "Store",
            "name": "Nom du magasin",
            "image": "https://www.example.com/store.jpg",
            "telephone": "+33-1-23-45-67-89",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'Hospital': {
            "@context": "https://schema.org",
            "@type": "Hospital",
            "name": "Nom de l'hôpital",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "telephone": "+33-1-23-45-67-89",
            "medicalSpecialty": "Médecine générale"
        },
        'School': {
            "@context": "https://schema.org",
            "@type": "School",
            "name": "Nom de l'école",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'University': {
            "@context": "https://schema.org",
            "@type": "University",
            "name": "Nom de l'université",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'NGO': {
            "@context": "https://schema.org",
            "@type": "NGO",
            "name": "Nom de l'ONG",
            "description": "Description de l'ONG",
            "url": "https://www.example.com"
        },
        
        # Person
        'Person': {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Prénom Nom",
            "jobTitle": "Titre du poste",
            "worksFor": {
                "@type": "Organization",
                "name": "Nom de l'organisation"
            },
            "url": "https://www.example.com/profile",
            "image": "https://www.example.com/photo.jpg",
            "email": "email@example.com",
            "telephone": "+33-1-23-45-67-89"
        },
        
        # Place types
        'Place': {
            "@context": "https://schema.org",
            "@type": "Place",
            "name": "Nom du lieu",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": "48.8566",
                "longitude": "2.3522"
            }
        },
        'TouristAttraction': {
            "@context": "https://schema.org",
            "@type": "TouristAttraction",
            "name": "Attraction touristique",
            "description": "Description de l'attraction",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Paris",
                "addressCountry": "FR"
            }
        },
        'Accommodation': {
            "@context": "https://schema.org",
            "@type": "Accommodation",
            "name": "Nom de l'hébergement",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'Hotel': {
            "@context": "https://schema.org",
            "@type": "Hotel",
            "name": "Nom de l'hôtel",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "checkinTime": "15:00",
            "checkoutTime": "11:00"
        },
        
        # Product types
        'Product': {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Nom du produit",
            "image": "https://www.example.com/product.jpg",
            "description": "Description du produit",
            "brand": {
                "@type": "Brand",
                "name": "Marque"
            },
            "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "EUR",
                "availability": "https://schema.org/InStock",
                "seller": {
                    "@type": "Organization",
                    "name": "Vendeur"
                }
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.5",
                "reviewCount": "123"
            }
        },
        'Service': {
            "@context": "https://schema.org",
            "@type": "Service",
            "name": "Nom du service",
            "description": "Description du service",
            "provider": {
                "@type": "Organization",
                "name": "Prestataire"
            },
            "areaServed": "Paris",
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "Catalogue de services"
            }
        },
        
        # Intangible types
        'Brand': {
            "@context": "https://schema.org",
            "@type": "Brand",
            "name": "Nom de la marque",
            "logo": "https://www.example.com/logo.png",
            "url": "https://www.example.com"
        },
        'Rating': {
            "@context": "https://schema.org",
            "@type": "Rating",
            "ratingValue": "4.5",
            "bestRating": "5",
            "worstRating": "1"
        },
        'Review': {
            "@context": "https://schema.org",
            "@type": "Review",
            "reviewBody": "Texte de l'avis",
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": "5",
                "bestRating": "5"
            },
            "author": {
                "@type": "Person",
                "name": "Nom du reviewer"
            },
            "itemReviewed": {
                "@type": "Thing",
                "name": "Produit/Service évalué"
            }
        },
        'AggregateRating': {
            "@context": "https://schema.org",
            "@type": "AggregateRating",
            "ratingValue": "4.5",
            "reviewCount": "123",
            "bestRating": "5",
            "worstRating": "1"
        },
        'ContactPoint': {
            "@context": "https://schema.org",
            "@type": "ContactPoint",
            "telephone": "+33-1-23-45-67-89",
            "contactType": "customer service",
            "areaServed": "FR",
            "availableLanguage": ["French", "English"]
        },
        'PostalAddress': {
            "@context": "https://schema.org",
            "@type": "PostalAddress",
            "streetAddress": "123 Rue Example",
            "addressLocality": "Paris",
            "postalCode": "75001",
            "addressCountry": "FR"
        },
        'GeoCoordinates': {
            "@context": "https://schema.org",
            "@type": "GeoCoordinates",
            "latitude": "48.8566",
            "longitude": "2.3522"
        },
        'Offer': {
            "@context": "https://schema.org",
            "@type": "Offer",
            "price": "29.99",
            "priceCurrency": "EUR",
            "availability": "https://schema.org/InStock",
            "validFrom": "2024-01-01",
            "validThrough": "2024-12-31"
        },
        'JobPosting': {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Intitulé du poste",
            "description": "Description du poste",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "Nom de l'entreprise"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Paris",
                    "addressCountry": "FR"
                }
            },
            "employmentType": "FULL_TIME",
            "datePosted": "2024-01-01"
        },
        
        # FAQ/HowTo
        'FAQPage': {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "Question fréquente ?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Réponse à la question fréquente."
                    }
                }
            ]
        },
        'HowTo': {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": "Comment faire quelque chose",
            "description": "Description du tutoriel",
            "step": [
                {
                    "@type": "HowToStep",
                    "text": "Première étape"
                },
                {
                    "@type": "HowToStep",
                    "text": "Deuxième étape"
                }
            ]
        },
        
        # Navigation
        'BreadcrumbList': {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Accueil",
                    "item": "https://www.example.com"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Catégorie",
                    "item": "https://www.example.com/category"
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": "Page actuelle"
                }
            ]
        },
        'ItemList': {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Liste d'éléments",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Premier élément"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Deuxième élément"
                }
            ]
        },
        'ListItem': {
            "@context": "https://schema.org",
            "@type": "ListItem",
            "position": 1,
            "name": "Nom de l'élément",
            "item": "https://www.example.com/item"
        },
        
        # Medical types
        'MedicalEntity': {
            "@context": "https://schema.org",
            "@type": "MedicalEntity",
            "name": "Entité médicale",
            "description": "Description médicale"
        },
        'MedicalCondition': {
            "@context": "https://schema.org",
            "@type": "MedicalCondition",
            "name": "Condition médicale",
            "description": "Description de la condition"
        },
        'Drug': {
            "@context": "https://schema.org",
            "@type": "Drug",
            "name": "Nom du médicament",
            "activeIngredient": "Principe actif"
        },
        'MedicalProcedure': {
            "@context": "https://schema.org",
            "@type": "MedicalProcedure",
            "name": "Procédure médicale",
            "description": "Description de la procédure"
        },
        
        # Social Media
        'SocialMediaPosting': {
            "@context": "https://schema.org",
            "@type": "SocialMediaPosting",
            "headline": "Titre du post",
            "articleBody": "Contenu du post",
            "author": {
                "@type": "Person",
                "name": "Auteur"
            },
            "datePublished": "2024-01-01"
        },
        
        # Vehicle types
        'Vehicle': {
            "@context": "https://schema.org",
            "@type": "Vehicle",
            "name": "Nom du véhicule",
            "brand": {
                "@type": "Brand",
                "name": "Marque"
            },
            "model": "Modèle",
            "vehicleModelDate": "2024"
        },
        'Car': {
            "@context": "https://schema.org",
            "@type": "Car",
            "name": "Voiture",
            "brand": {
                "@type": "Brand",
                "name": "Constructeur"
            },
            "model": "Modèle",
            "fuelType": "Essence"
        },
        
        # Real Estate
        'RealEstateListing': {
            "@context": "https://schema.org",
            "@type": "RealEstateListing",
            "name": "Annonce immobilière",
            "description": "Description du bien",
            "price": "250000",
            "priceCurrency": "EUR",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            }
        },
        'House': {
            "@context": "https://schema.org",
            "@type": "House",
            "name": "Maison",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "numberOfRooms": "5"
        },
        'Apartment': {
            "@context": "https://schema.org",
            "@type": "Apartment",
            "name": "Appartement",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Rue Example",
                "addressLocality": "Paris",
                "postalCode": "75001",
                "addressCountry": "FR"
            },
            "numberOfRooms": "3"
        },
        
        # Sports
        'SportsTeam': {
            "@context": "https://schema.org",
            "@type": "SportsTeam",
            "name": "Nom de l'équipe",
            "sport": "Football",
            "location": {
                "@type": "Place",
                "name": "Ville"
            }
        },
        'SportsOrganization': {
            "@context": "https://schema.org",
            "@type": "SportsOrganization",
            "name": "Organisation sportive",
            "sport": "Football"
        },
        
        # Gaming
        'Game': {
            "@context": "https://schema.org",
            "@type": "Game",
            "name": "Nom du jeu",
            "description": "Description du jeu",
            "genre": "Action"
        },
        'VideoGame': {
            "@context": "https://schema.org",
            "@type": "VideoGame",
            "name": "Nom du jeu vidéo",
            "description": "Description du jeu",
            "gamePlatform": "PC, PlayStation, Xbox"
        },
        
        # Music
        'MusicGroup': {
            "@context": "https://schema.org",
            "@type": "MusicGroup",
            "name": "Nom du groupe",
            "genre": "Rock",
            "member": [
                {
                    "@type": "Person",
                    "name": "Membre 1"
                }
            ]
        },
        'MusicAlbum': {
            "@context": "https://schema.org",
            "@type": "MusicAlbum",
            "name": "Nom de l'album",
            "byArtist": {
                "@type": "MusicGroup",
                "name": "Artiste"
            },
            "datePublished": "2024-01-01"
        },
        'MusicRecording': {
            "@context": "https://schema.org",
            "@type": "MusicRecording",
            "name": "Titre de la chanson",
            "byArtist": {
                "@type": "MusicGroup",
                "name": "Artiste"
            },
            "duration": "PT3M30S"
        },
        
        # Financial
        'FinancialProduct': {
            "@context": "https://schema.org",
            "@type": "FinancialProduct",
            "name": "Produit financier",
            "description": "Description du produit"
        },
        'BankAccount': {
            "@context": "https://schema.org",
            "@type": "BankAccount",
            "name": "Compte bancaire",
            "provider": {
                "@type": "BankOrCreditUnion",
                "name": "Banque"
            }
        },
        'LoanOrCredit': {
            "@context": "https://schema.org",
            "@type": "LoanOrCredit",
            "name": "Prêt ou crédit",
            "amount": {
                "@type": "MonetaryAmount",
                "value": "10000",
                "currency": "EUR"
            }
        },
        
        # Government
        'GovernmentOrganization': {
            "@context": "https://schema.org",
            "@type": "GovernmentOrganization",
            "name": "Organisation gouvernementale",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Paris",
                "addressCountry": "FR"
            }
        },
        'GovernmentBuilding': {
            "@context": "https://schema.org",
            "@type": "GovernmentBuilding",
            "name": "Bâtiment gouvernemental",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Paris",
                "addressCountry": "FR"
            }
        },
        
        # Compatibility types
        'OpenGraph': {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Titre de la page",
            "description": "Description pour les réseaux sociaux",
            "image": "https://www.example.com/og-image.jpg",
            "url": "https://www.example.com"
        },
        'TwitterCard': {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Titre pour Twitter",
            "description": "Description pour Twitter",
            "image": "https://www.example.com/twitter-image.jpg"
        },
        'MetaTags': {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Titre de la page",
            "description": "Meta description de la page",
            "keywords": "mot-clé1, mot-clé2, mot-clé3"
        }
    }
    
    # Si le type exact existe, le retourner
    if data_type in examples:
        return json.dumps(examples[data_type], indent=2, ensure_ascii=False)
    
    # Sinon, essayer de trouver un type similaire (sans casse)
    data_type_lower = data_type.lower()
    for key in examples.keys():
        if key.lower() == data_type_lower:
            return json.dumps(examples[key], indent=2, ensure_ascii=False)
    
    # Recherche partielle pour les types composés (ex: "LocalBusiness" pour "Restaurant")
    for key in examples.keys():
        if data_type_lower in key.lower() or key.lower() in data_type_lower:
            return json.dumps(examples[key], indent=2, ensure_ascii=False)
    
    # Si aucune correspondance, retourner un exemple générique
    generic_example = {
        "@context": "https://schema.org",
        "@type": data_type,
        "name": f"Exemple de {data_type}",
        "description": f"Description générique pour le type {data_type}",
        "url": "https://www.example.com"
    }
    
    return json.dumps(generic_example, indent=2, ensure_ascii=False)

def compare_structured_data(client_data: Dict[str, List[Dict]], competitors_data: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Dict]:
    """Compare les données structurées et retourne un dictionnaire organisé avec les résultats"""
    client_types = get_data_types_set(client_data)
    
    missing_data = {}
    all_competitor_types = set()
    
    # Collecter tous les types présents chez les concurrents
    for competitor_name, competitor_data in competitors_data.items():
        competitor_types = get_data_types_set(competitor_data)
        all_competitor_types.update(competitor_types)
        
        # Données présentes chez le concurrent mais absentes chez le client
        missing_types = competitor_types - client_types
        
        for data_type in missing_types:
            if data_type not in missing_data:
                missing_data[data_type] = {
                    'competitors_with_data': [],
                    'example_from_competitor': None,
                    'schema_org_example': get_schema_org_example(data_type)
                }
            
            missing_data[data_type]['competitors_with_data'].append(competitor_name)
            
            # Récupérer un exemple depuis le concurrent si pas encore fait
            if missing_data[data_type]['example_from_competitor'] is None:
                competitor_flattened = flatten_data_for_comparison(competitor_data)
                matching_keys = [k for k in competitor_flattened.keys() if data_type in k]
                if matching_keys:
                    missing_data[data_type]['example_from_competitor'] = json.dumps(
                        competitor_flattened[matching_keys[0]], 
                        indent=2, 
                        ensure_ascii=False
                    )
    
    return missing_data

def main():
    st.set_page_config(
        page_title="Comparateur de données structurées",
        layout="wide"
    )
    
    # Style CSS pour le bouton
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #f6f6ec !important;
        color: #76520e !important;
        border: 1px solid #76520e !important;
    }
    .stButton > button:hover {
        background-color: #eeeedc !important;
        color: #76520e !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Comparateur de données structurées")
    st.markdown("Analysez et comparez les données structurées entre votre site et vos concurrents")
    
    # Zone d'entrée pour le client
    st.header("Votre site web")
    client_html = st.text_area(
        "Collez le code HTML complet de votre page :",
        height=200,
        placeholder="<html>...</html>"
    )
    
    # Zones d'entrée pour les concurrents
    st.header("Sites concurrents")
    
    num_competitors = st.number_input(
        "Nombre de concurrents à analyser :",
        min_value=1,
        max_value=10,
        value=2
    )
    
    competitors_data = {}
    for i in range(num_competitors):
        col1, col2 = st.columns([1, 4])
        with col1:
            competitor_name = st.text_input(
                f"Nom concurrent {i+1}:",
                value=f"Concurrent {i+1}",
                key=f"name_{i}"
            )
        with col2:
            competitor_html = st.text_area(
                f"Code HTML du concurrent {i+1} :",
                height=150,
                placeholder="<html>...</html>",
                key=f"html_{i}"
            )
            
        if competitor_html.strip():
            competitors_data[competitor_name] = competitor_html
    
    # Bouton d'analyse
    if st.button("Analyser et comparer", type="primary"):
        if not client_html.strip():
            st.error("Veuillez entrer le code HTML de votre site.")
            return
        
        if not competitors_data:
            st.error("Veuillez entrer au moins un concurrent.")
            return
        
        with st.spinner("Analyse en cours..."):
            # Extraction des données structurées du client
            client_structured_data = extract_structured_data(client_html)
            
            # Extraction des données structurées des concurrents
            competitors_structured_data = {}
            for name, html in competitors_data.items():
                competitors_structured_data[name] = extract_structured_data(html)
            
            # Comparaison
            comparison_results = compare_structured_data(client_structured_data, competitors_structured_data)
            
        # Affichage des résultats
        st.header("Résultats de l'analyse")
        
        # Données structurées du client
        st.subheader("Vos données structurées")
        if client_structured_data:
            for category, data_list in client_structured_data.items():
                with st.expander(f"{category} ({len(data_list)} élément(s))"):
                    for i, data in enumerate(data_list):
                        st.json(data)
        else:
            st.warning("Aucune donnée structurée trouvée sur votre site.")
        
        # Données manquantes
        st.subheader("Données structurées manquantes")
        
        if comparison_results:
            st.info(f"**{len(comparison_results)} type(s) de données structurées** sont présents chez vos concurrents mais absents de votre site.")
            
            for data_type, info in comparison_results.items():
                competitors_list = ", ".join(info['competitors_with_data'])
                st.write(f"**{data_type}**")
                st.write(f"*Présent chez : {competitors_list}*")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    with st.expander("Voir l'exemple du concurrent"):
                        if info['example_from_competitor']:
                            st.code(info['example_from_competitor'], language='json')
                        else:
                            st.write("Aucun exemple disponible")
                
                with col2:
                    with st.expander("Voir l'exemple Schema.org recommandé"):
                        st.code(info['schema_org_example'], language='json')
                
                st.divider()
            
            # Créer un DataFrame pour l'export CSV
            export_data = []
            for data_type, info in comparison_results.items():
                export_data.append({
                    'Type de données manquant': data_type,
                    'Concurrents avec cette donnée': ", ".join(info['competitors_with_data']),
                    'Exemple Schema.org': info['schema_org_example'],
                    'Exemple du concurrent': info['example_from_competitor'] or "Non disponible"
                })
            
            export_df = pd.DataFrame(export_data)
            
            # Bouton de téléchargement
            csv_buffer = io.StringIO()
            export_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="Télécharger les résultats (CSV)",
                data=csv_data,
                file_name="donnees_structurees_manquantes.csv",
                mime="text/csv"
            )
            
            # Statistiques
            st.subheader("Statistiques")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Types de données manquants", len(comparison_results))
            
            with col2:
                total_competitors = len(competitors_structured_data)
                st.metric("Concurrents analysés", total_competitors)
            
            with col3:
                most_common = max(comparison_results.items(), key=lambda x: len(x[1]['competitors_with_data']))[0] if comparison_results else "N/A"
                st.metric("Type le plus fréquent", most_common)
            
        else:
            st.success("Excellente nouvelle ! Votre site contient toutes les données structurées présentes chez vos concurrents.")
        
        # Données des concurrents
        st.subheader("Données structurées des concurrents")
        
        for competitor_name, competitor_data in competitors_structured_data.items():
            with st.expander(f"{competitor_name}"):
                if competitor_data:
                    for category, data_list in competitor_data.items():
                        st.write(f"**{category}** ({len(data_list)} élément(s))")
                        for i, data in enumerate(data_list):
                            with st.container():
                                st.json(data)
                else:
                    st.warning(f"Aucune donnée structurée trouvée pour {competitor_name}")

if __name__ == "__main__":
    main()
