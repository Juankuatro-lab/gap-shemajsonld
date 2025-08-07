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

def compare_structured_data(client_data: Dict[str, List[Dict]], competitors_data: Dict[str, Dict[str, List[Dict]]]) -> pd.DataFrame:
    """Compare les données structurées et retourne un DataFrame avec les résultats"""
    client_types = get_data_types_set(client_data)
    client_flattened = flatten_data_for_comparison(client_data)
    
    comparison_results = []
    
    # Analyser chaque concurrent
    for competitor_name, competitor_data in competitors_data.items():
        competitor_types = get_data_types_set(competitor_data)
        competitor_flattened = flatten_data_for_comparison(competitor_data)
        
        # Données présentes chez le concurrent mais absentes chez le client
        missing_types = competitor_types - client_types
        
        for data_type in missing_types:
            # Trouver les données correspondantes dans competitor_flattened
            matching_keys = [k for k in competitor_flattened.keys() if data_type in k]
            
            for key in matching_keys:
                competitor_data_item = competitor_flattened[key]
                comparison_results.append({
                    'Concurrent': competitor_name,
                    'Type de données manquant': data_type,
                    'Propriétés': ', '.join([k for k in competitor_data_item.keys() if k != '@type']),
                    'Exemple de code': json.dumps(competitor_data_item, indent=2, ensure_ascii=False)
                })
        
        # Également analyser les propriétés manquantes pour les types existants
        common_types = client_types.intersection(competitor_types)
        for data_type in common_types:
            client_keys = [k for k in client_flattened.keys() if data_type in k]
            competitor_keys = [k for k in competitor_flattened.keys() if data_type in k]
            
            if client_keys and competitor_keys:
                client_props = set()
                for key in client_keys:
                    client_props.update(client_flattened[key].keys())
                
                for key in competitor_keys:
                    competitor_props = set(competitor_flattened[key].keys())
                    missing_props = competitor_props - client_props
                    
                    if missing_props:
                        comparison_results.append({
                            'Concurrent': competitor_name,
                            'Type de données manquant': f"{data_type} (propriétés manquantes)",
                            'Propriétés': ', '.join(missing_props),
                            'Exemple de code': json.dumps({k: v for k, v in competitor_flattened[key].items() if k in missing_props}, indent=2, ensure_ascii=False)
                        })
    
    return pd.DataFrame(comparison_results)

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
    st.header("Votre site web (client)")
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
            comparison_df = compare_structured_data(client_structured_data, competitors_structured_data)
            
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
        
        if not comparison_df.empty:
            st.dataframe(comparison_df, use_container_width=True)
            
            # Bouton de téléchargement
            csv_buffer = io.StringIO()
            comparison_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
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
                st.metric("Types de données manquants", len(comparison_df['Type de données manquant'].unique()))
            
            with col2:
                st.metric("Total des opportunités", len(comparison_df))
            
            with col3:
                most_common = comparison_df['Type de données manquant'].value_counts().index[0] if not comparison_df.empty else "N/A"
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
