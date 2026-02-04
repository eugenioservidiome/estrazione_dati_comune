"""Query generation for document retrieval."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Synonym dictionary for query expansion
SYNONYMS = {
    'delibere': ['deliberazioni', 'delibera', 'decreto', 'atto'],
    'consiglio': ['cc', 'consiglio comunale', 'council'],
    'giunta': ['gc', 'giunta comunale', 'giunta municipale'],
    'personale': ['dipendenti', 'organico', 'risorse umane', 'staff'],
    'struttura': ['organigramma', 'organizzazione', 'organizational chart'],
    'patrimonio': ['asset', 'patrimonio netto', 'equity'],
    'debiti': ['debito', 'passività', 'liabilities'],
    'investimenti': ['investimento', 'spese in conto capitale'],
    'rifiuti': ['rsu', 'raccolta differenziata', 'waste'],
    'biblioteca': ['biblioteche', 'library', 'prestiti libri']
}

# Query templates for internal (domain) sources
QUERY_TEMPLATES = {
    'DELIBERE_CC': [
        'site:{DOMAIN} deliberazioni consiglio comunale {YEAR}',
        'site:{DOMAIN} delibere cc {YEAR} filetype:pdf',
        'site:{DOMAIN} inurl:albo deliberazioni consiglio {YEAR}',
        '"{COMUNE}" delibere consiglio comunale {YEAR} filetype:pdf',
        'site:{DOMAIN} "delibera" AND "consiglio comunale" AND "{YEAR}"',
        'site:{DOMAIN} albo pretorio deliberazioni cc {YEAR_WORD}',
        '"{COMUNE}" atti consiglio comunale {YEAR}',
        'site:{DOMAIN} inurl:delibere consiglio {YEAR}',
        'site:{DOMAIN} "numero delibera" consiglio {YEAR} filetype:pdf',
        'deliberazioni consiglio "{COMUNE}" {YEAR} site:{DOMAIN}'
    ],
    
    'DELIBERE_GC': [
        'site:{DOMAIN} deliberazioni giunta comunale {YEAR}',
        'site:{DOMAIN} delibere gc {YEAR} filetype:pdf',
        'site:{DOMAIN} inurl:albo deliberazioni giunta {YEAR}',
        '"{COMUNE}" delibere giunta comunale {YEAR} filetype:pdf',
        'site:{DOMAIN} "delibera" AND "giunta comunale" AND "{YEAR}"',
        'site:{DOMAIN} albo pretorio deliberazioni giunta {YEAR_WORD}',
        '"{COMUNE}" atti giunta {YEAR}',
        'site:{DOMAIN} inurl:delibere giunta {YEAR}',
        'site:{DOMAIN} "numero delibera" giunta {YEAR} filetype:pdf',
        'deliberazioni giunta "{COMUNE}" {YEAR} site:{DOMAIN}'
    ],
    
    'SEDUTE_CC': [
        'site:{DOMAIN} sedute consiglio comunale {YEAR}',
        'site:{DOMAIN} verbali consiglio {YEAR} filetype:pdf',
        '"{COMUNE}" sedute cc {YEAR}',
        'site:{DOMAIN} "ordine del giorno" consiglio {YEAR}',
        'site:{DOMAIN} inurl:consiglio sedute {YEAR}',
        'convocazioni consiglio comunale "{COMUNE}" {YEAR}',
        'site:{DOMAIN} "consiglio comunale" riunioni {YEAR}'
    ],
    
    'SEDUTE_GC': [
        'site:{DOMAIN} sedute giunta comunale {YEAR}',
        'site:{DOMAIN} verbali giunta {YEAR} filetype:pdf',
        '"{COMUNE}" sedute giunta {YEAR}',
        'site:{DOMAIN} "ordine del giorno" giunta {YEAR}',
        'site:{DOMAIN} inurl:giunta sedute {YEAR}',
        'convocazioni giunta comunale "{COMUNE}" {YEAR}',
        'site:{DOMAIN} "giunta comunale" riunioni {YEAR}'
    ],
    
    'PERSONALE': [
        'site:{DOMAIN} personale dipendenti {YEAR}',
        'site:{DOMAIN} organico comunale {YEAR} filetype:pdf',
        '"{COMUNE}" dotazione organica {YEAR}',
        'site:{DOMAIN} "numero dipendenti" {YEAR}',
        'site:{DOMAIN} inurl:personale dotazione {YEAR}',
        'risorse umane "{COMUNE}" {YEAR}',
        'site:{DOMAIN} "pianta organica" {YEAR}',
        'site:{DOMAIN} "conto annuale" personale {YEAR}',
        'dipendenti comunali "{COMUNE}" {YEAR} site:{DOMAIN}'
    ],
    
    'STRUTTURA': [
        'site:{DOMAIN} organigramma {YEAR}',
        'site:{DOMAIN} struttura organizzativa {YEAR} filetype:pdf',
        '"{COMUNE}" organigramma comunale {YEAR}',
        'site:{DOMAIN} "organizational chart" {YEAR}',
        'site:{DOMAIN} inurl:organigramma {YEAR}',
        'struttura amministrativa "{COMUNE}" {YEAR}',
        'site:{DOMAIN} "assetto organizzativo" {YEAR}'
    ],
    
    'SERVIZIO_CIVILE': [
        'site:{DOMAIN} servizio civile {YEAR}',
        '"{COMUNE}" volontari servizio civile {YEAR}',
        'site:{DOMAIN} "servizio civile universale" {YEAR}',
        'site:{DOMAIN} inurl:servizio-civile {YEAR}',
        'bandi servizio civile "{COMUNE}" {YEAR}',
        'site:{DOMAIN} progetti servizio civile {YEAR}'
    ],
    
    'PERSONALE_ETA_GENERE': [
        'site:{DOMAIN} personale età genere {YEAR}',
        'site:{DOMAIN} "fasce di età" dipendenti {YEAR} filetype:pdf',
        '"{COMUNE}" dipendenti età sesso {YEAR}',
        'site:{DOMAIN} "composizione del personale" età genere {YEAR}',
        'anagrafica dipendenti "{COMUNE}" {YEAR}'
    ],
    
    'PATRIMONIO_NETTO': [
        'site:{DOMAIN} patrimonio netto {YEAR}',
        'site:{DOMAIN} bilancio patrimonio {YEAR} filetype:pdf',
        '"{COMUNE}" patrimonio comunale {YEAR}',
        'site:{DOMAIN} "stato patrimoniale" {YEAR}',
        'site:{DOMAIN} inurl:bilancio patrimonio {YEAR}',
        'rendiconto patrimonio netto "{COMUNE}" {YEAR}'
    ],
    
    'DEBITI': [
        'site:{DOMAIN} debiti {YEAR}',
        'site:{DOMAIN} esposizione debitoria {YEAR} filetype:pdf',
        '"{COMUNE}" debito comunale {YEAR}',
        'site:{DOMAIN} "stock di debito" {YEAR}'
    ],
    
    'RISULTATO_ECONOMICO': [
        'site:{DOMAIN} risultato economico {YEAR}',
        'site:{DOMAIN} conto economico {YEAR} filetype:pdf',
        '"{COMUNE}" risultato di amministrazione {YEAR}'
    ],
    
    'INVESTIMENTI_MISSIONE': [
        'site:{DOMAIN} investimenti missione {MISSIONE} {YEAR}',
        'site:{DOMAIN} spese investimento "{MISSIONE}" {YEAR} filetype:pdf',
        '"{COMUNE}" investimenti {MISSIONE} {YEAR}',
        'site:{DOMAIN} "spese in conto capitale" missione {MISSIONE} {YEAR}'
    ],
    
    'SOCIAL_MEDIA': [
        'site:{DOMAIN} {SOCIAL}',
        '"{COMUNE}" {SOCIAL} ufficiale',
        'pagina {SOCIAL} "{COMUNE}"',
        '{SOCIAL}.com/{COMUNE}'
    ],
    
    'POLIZIA_LOCALE': [
        'site:{DOMAIN} polizia locale {YEAR}',
        'site:{DOMAIN} vigili urbani {YEAR} filetype:pdf',
        '"{COMUNE}" polizia municipale organico {YEAR}',
        'site:{DOMAIN} "corpo di polizia locale" {YEAR}'
    ],
    
    'ART_208_CDS': [
        'site:{DOMAIN} art 208 cds {YEAR}',
        'site:{DOMAIN} "articolo 208" codice della strada {YEAR} filetype:pdf',
        '"{COMUNE}" proventi articolo 208 {YEAR}'
    ],
    
    'EDILIZIA': [
        'site:{DOMAIN} permessi costruire {YEAR}',
        'site:{DOMAIN} edilizia titoli abilitativi {YEAR} filetype:pdf',
        '"{COMUNE}" concessioni edilizie {YEAR}',
        'site:{DOMAIN} "pratiche edilizie" {YEAR}'
    ],
    
    'MANUTENZIONI': [
        'site:{DOMAIN} manutenzioni {YEAR}',
        'site:{DOMAIN} "manutenzione ordinaria" {YEAR} filetype:pdf',
        '"{COMUNE}" interventi manutenzione {YEAR}'
    ],
    
    'BIBLIOTECA': [
        'site:{DOMAIN} biblioteca {YEAR}',
        'site:{DOMAIN} prestiti libri {YEAR} filetype:pdf',
        '"{COMUNE}" servizi biblioteca {YEAR}'
    ],
    
    'RIFIUTI_RD': [
        'site:{DOMAIN} raccolta differenziata {YEAR}',
        'site:{DOMAIN} percentuale differenziata {YEAR} filetype:pdf',
        '"{COMUNE}" rifiuti raccolta differenziata {YEAR}',
        'site:{DOMAIN} "rsu" differenziata {YEAR}'
    ],
    
    'RIFIUTI_FRAZIONE': [
        'site:{DOMAIN} raccolta {FRAZIONE} {YEAR}',
        '"{COMUNE}" rifiuti {FRAZIONE} {YEAR} filetype:pdf'
    ],
    
    'PROGETTI_PNRR': [
        'site:{DOMAIN} PNRR {YEAR}',
        'site:{DOMAIN} progetti PNRR {YEAR} filetype:pdf',
        '"{COMUNE}" piano nazionale ripresa resilienza {YEAR}',
        'site:{DOMAIN} "fondi PNRR" {YEAR}'
    ],
    
    'PROGETTI_OPERE': [
        'site:{DOMAIN} opere pubbliche {YEAR}',
        'site:{DOMAIN} lavori pubblici {YEAR} filetype:pdf',
        '"{COMUNE}" programma opere pubbliche {YEAR}'
    ],
    
    'GENERIC': [
        'site:{DOMAIN} "{LABEL}" {YEAR}',
        'site:{DOMAIN} {LABEL} {YEAR} filetype:pdf',
        '"{COMUNE}" {LABEL} {YEAR}',
        'site:{DOMAIN} inurl:{LABEL} {YEAR}',
        '{LABEL} comune "{COMUNE}" {YEAR}'
    ]
}

# External query templates (official sources)
EXTERNAL_QUERY_TEMPLATES = {
    'ISTAT_POPOLAZIONE': [
        'site:istat.it popolazione residente "{COMUNE}" {YEAR}',
        'site:dati.istat.it popolazione {YEAR} "{COMUNE}"',
        'ISTAT popolazione comunale "{COMUNE}" {YEAR} filetype:xls',
        'site:istat.it demo popolazione {YEAR}'
    ],
    
    'ISTAT_NATI_MORTI': [
        'site:istat.it nati morti "{COMUNE}" {YEAR}',
        'site:dati.istat.it movimento naturale {YEAR} "{COMUNE}"',
        'ISTAT natalità mortalità "{COMUNE}" {YEAR}'
    ],
    
    'ISTAT_STRANIERI': [
        'site:istat.it stranieri residenti "{COMUNE}" {YEAR}',
        'site:dati.istat.it popolazione straniera {YEAR}'
    ],
    
    'ISPRA_RIFIUTI': [
        'site:isprambiente.gov.it rifiuti urbani "{COMUNE}" {YEAR}',
        'ISPRA rapporto rifiuti urbani {YEAR} filetype:pdf'
    ],
    
    'MEF_IMU': [
        'site:finanze.gov.it IMU "{COMUNE}" {YEAR}',
        'MEF gettito IMU comunale {YEAR}'
    ],
    
    'MEF_IRPEF': [
        'site:finanze.gov.it IRPEF "{COMUNE}" {YEAR}',
        'MEF addizionale IRPEF comunale {YEAR}'
    ],
    
    'BDAP_CONTABILI': [
        'site:bdap.tesoro.it "{COMUNE}" bilancio {YEAR}',
        'OpenCivitas "{COMUNE}" dati contabili {YEAR}'
    ]
}


def categorize_cell(row_label: str, section_context: str = "") -> str:
    """Categorize a cell based on row label and section context.
    
    Args:
        row_label: Label from the CSV row
        section_context: Section header text (if any)
        
    Returns:
        Category string for query template selection
    """
    row_lower = row_label.lower()
    section_lower = section_context.lower() if section_context else ""
    
    # Deliberazioni
    if 'deliber' in row_lower or 'deliber' in section_lower:
        if 'giunta' in row_lower or 'giunta' in section_lower or 'gc' in row_lower:
            return 'DELIBERE_GC'
        elif 'consiglio' in row_lower or 'consiglio' in section_lower or 'cc' in row_lower:
            return 'DELIBERE_CC'
        return 'DELIBERE_CC'  # default
    
    # Sedute
    if 'sedut' in row_lower or 'sedut' in section_lower or 'convocaz' in row_lower:
        if 'giunta' in row_lower or 'giunta' in section_lower:
            return 'SEDUTE_GC'
        elif 'consiglio' in row_lower or 'consiglio' in section_lower:
            return 'SEDUTE_CC'
        return 'SEDUTE_CC'
    
    # Personale
    if any(kw in row_lower for kw in ['dipendent', 'personale', 'organico', 'dotazione']):
        if any(kw in row_lower for kw in ['età', 'genere', 'sesso', 'fasc']):
            return 'PERSONALE_ETA_GENERE'
        return 'PERSONALE'
    
    # Struttura organizzativa
    if any(kw in row_lower for kw in ['organigramma', 'struttura', 'organizzativ']):
        return 'STRUTTURA'
    
    # Servizio civile
    if 'servizio civile' in row_lower or 'volontar' in row_lower:
        return 'SERVIZIO_CIVILE'
    
    # Patrimonio
    if 'patrimonio' in row_lower:
        return 'PATRIMONIO_NETTO'
    
    # Debiti
    if 'debit' in row_lower or 'passività' in row_lower:
        return 'DEBITI'
    
    # Risultato economico
    if 'risultato' in row_lower and ('economic' in row_lower or 'amministraz' in row_lower):
        return 'RISULTATO_ECONOMICO'
    
    # Investimenti
    if 'investiment' in row_lower or 'spese in conto capitale' in row_lower:
        if any(kw in row_lower for kw in ['mission', 'settore', 'area']):
            return 'INVESTIMENTI_MISSIONE'
        return 'INVESTIMENTI_MISSIONE'
    
    # Social media
    if any(kw in row_lower for kw in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'social']):
        return 'SOCIAL_MEDIA'
    
    # Polizia locale
    if any(kw in row_lower for kw in ['polizia', 'vigili', 'municipal']):
        return 'POLIZIA_LOCALE'
    
    # Art. 208 CDS
    if '208' in row_lower or ('art' in row_lower and 'strada' in row_lower):
        return 'ART_208_CDS'
    
    # Edilizia
    if any(kw in row_lower for kw in ['edili', 'permess', 'concessio', 'costrui']):
        return 'EDILIZIA'
    
    # Manutenzioni
    if 'manutenz' in row_lower:
        return 'MANUTENZIONI'
    
    # Biblioteca
    if 'bibliote' in row_lower or 'prestit' in row_lower:
        return 'BIBLIOTECA'
    
    # Rifiuti
    if 'rifiut' in row_lower or 'rsu' in row_lower or 'raccolta' in row_lower:
        if 'differenziat' in row_lower:
            return 'RIFIUTI_RD'
        if any(kw in row_lower for kw in ['organic', 'carta', 'plastica', 'vetro', 'secco']):
            return 'RIFIUTI_FRAZIONE'
        return 'RIFIUTI_RD'
    
    # PNRR
    if 'pnrr' in row_lower or 'ripresa' in row_lower:
        return 'PROGETTI_PNRR'
    
    # Opere pubbliche
    if any(kw in row_lower for kw in ['opere', 'lavori', 'pubbl']):
        return 'PROGETTI_OPERE'
    
    # Default
    return 'GENERIC'


def _remove_search_operators(query: str) -> str:
    """Remove search engine operators from query to get semantic version.
    
    Args:
        query: Query with operators (site:, filetype:, inurl:, etc.)
        
    Returns:
        Clean semantic query
    """
    # Remove operators
    clean = re.sub(r'\b(site|filetype|inurl|intitle):[^\s]+', '', query)
    
    # Remove AND/OR operators
    clean = re.sub(r'\b(AND|OR)\b', '', clean)
    
    # Remove quotes (but keep the content)
    clean = clean.replace('"', '')
    
    # Clean up whitespace
    clean = ' '.join(clean.split())
    
    return clean.strip()


def _expand_with_synonyms(text: str) -> str:
    """Expand text with synonyms.
    
    Args:
        text: Text to expand
        
    Returns:
        Expanded text with synonyms added
    """
    text_lower = text.lower()
    expanded_parts = [text]
    
    for key, synonyms in SYNONYMS.items():
        if key in text_lower:
            # Add first synonym
            if synonyms:
                expanded_parts.append(synonyms[0])
    
    return ' '.join(expanded_parts)


def build_queries(category: str, domain: str, comune: str, year: int,
                 allow_external: bool = False,
                 extra_params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Build search queries for a given category.
    
    Args:
        category: Category string (e.g., 'DELIBERE_CC')
        domain: Website domain
        comune: Municipality name
        year: Year (int)
        allow_external: Whether to allow external official sources
        extra_params: Dict with optional params like 'MISSIONE', 'SOCIAL', 'FRAZIONE', 'LABEL'
    
    Returns:
        List of dicts with 'audit_query', 'semantic_query', 'priority', and 'category' keys
    """
    extra_params = extra_params or {}
    
    # Get templates
    templates = []
    
    # Check if category is external
    if category in EXTERNAL_QUERY_TEMPLATES:
        if not allow_external:
            logger.debug(f"Skipping external category {category} (external sources disabled)")
            return []
        templates = EXTERNAL_QUERY_TEMPLATES[category]
    else:
        templates = QUERY_TEMPLATES.get(category, QUERY_TEMPLATES['GENERIC'])
    
    # Year word mapping for Italian
    year_words = {
        2020: 'duemilaventi',
        2021: 'duemilaventuno',
        2022: 'duemilaventidue',
        2023: 'duemilaventitrè',
        2024: 'duemilaventiquattro',
        2025: 'duemilaventicinque'
    }
    year_word = year_words.get(year, str(year))
    
    queries = []
    for idx, template in enumerate(templates):
        # Create audit query (with operators)
        audit_query = template.replace('{DOMAIN}', domain)
        audit_query = audit_query.replace('{COMUNE}', comune)
        audit_query = audit_query.replace('{YEAR}', str(year))
        audit_query = audit_query.replace('{YEAR_WORD}', year_word)
        
        # Replace extra parameters
        if '{MISSIONE}' in audit_query:
            missione = extra_params.get('MISSIONE', 'servizi generali')
            audit_query = audit_query.replace('{MISSIONE}', missione)
        
        if '{SOCIAL}' in audit_query:
            social = extra_params.get('SOCIAL', 'facebook')
            audit_query = audit_query.replace('{SOCIAL}', social)
        
        if '{FRAZIONE}' in audit_query:
            frazione = extra_params.get('FRAZIONE', 'organico')
            audit_query = audit_query.replace('{FRAZIONE}', frazione)
        
        if '{LABEL}' in audit_query:
            label = extra_params.get('LABEL', '')
            audit_query = audit_query.replace('{LABEL}', label)
        
        # Create semantic query (no operators, with synonyms)
        semantic_query = _remove_search_operators(audit_query)
        semantic_query = _expand_with_synonyms(semantic_query)
        
        # Calculate priority (deterministic, based on template position and features)
        # Base priority: earlier templates are more specific (higher priority)
        priority = 10 - min(idx, 5)  # First templates get 10, 9, 8, 7, 6, later get 5
        
        # Bonus for specific features
        if 'filetype:pdf' in audit_query:
            priority += 2
        
        if 'site:' + domain in audit_query:
            priority += 1
        
        if 'inurl:' in audit_query:
            priority += 1
        
        if '"' in audit_query:  # has quoted terms
            priority += 1
        
        # Cap at 10
        priority = min(10, priority)
        
        queries.append({
            'audit_query': audit_query,
            'semantic_query': semantic_query,
            'priority': priority,
            'category': category
        })
    
    # Sort by priority (descending)
    queries.sort(key=lambda x: x['priority'], reverse=True)
    
    return queries
