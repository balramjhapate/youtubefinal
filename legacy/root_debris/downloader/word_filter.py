"""
Word Filter Module
Filters and replaces negative/abusive words with positive alternatives
"""
import re

# Dictionary of negative/abusive words and their positive replacements
# ALL WORD REPLACEMENTS COMMENTED OUT - Word filtering is disabled
WORD_REPLACEMENTS = {
    # Common negative words (Hindi) - ALL COMMENTED OUT
    # 'गंदा': 'साफ',
    # 'बुरा': 'अच्छा',
    # 'खराब': 'बेहतर',
    # 'बेकार': 'उपयोगी',
    # 'निराश': 'उत्साहित',
    # 'उदास': 'खुश',
    # 'क्रोधित': 'शांत',
    # 'गुस्सा': 'खुश',
    # 'झगड़ा': 'मित्रता',
    # 'लड़ाई': 'शांति',
    # 'हिंसा': 'शांति',
    # 'दुख': 'खुशी',
    # 'पीड़ा': 'सुख',
    # 'तकलीफ': 'आराम',
    # 'मुसीबत': 'आसानी',
    # 'परेशानी': 'सुविधा',
    # 'चिंता': 'शांति',
    # 'डर': 'साहस',  # REMOVED - fear is part of storytelling, should not be replaced
    # 'भय': 'आत्मविश्वास',  # REMOVED - fear is part of storytelling, should not be replaced
    # 'नफरत': 'प्यार',
    # 'घृणा': 'सम्मान',
    # 'अपमान': 'सम्मान',
    # 'बेइज्जती': 'इज्जत',
    # 'शर्म': 'गर्व',
    # 'लज्जा': 'गर्व',
    # 'अपराध': 'सही काम',
    # 'गलत': 'सही',
    # 'झूठ': 'सच',
    # 'धोखा': 'ईमानदारी',
    # 'चोरी': 'साझा',
    # 'हानि': 'लाभ',
    # 'नुकसान': 'फायदा',
    # 'हार': 'जीत',
    # 'असफल': 'सफल',
    # 'विफल': 'सफल',
    # 'कमजोर': 'मजबूत',
    # 'दुर्बल': 'शक्तिशाली',
    # 'बीमार': 'स्वस्थ',
    # 'रोगी': 'स्वस्थ',
    # 'मरना': 'जीना',
    # 'मौत': 'जीवन',
    # 'नष्ट': 'बनाना',
    # 'तोड़ना': 'बनाना',
    # 'बर्बाद': 'सुधार',
    # 'खत्म': 'शुरू',
    # 'अंत': 'शुरुआत',
    # 'अंधेरा': 'उजाला',  # REMOVED - darkness is part of storytelling, should not be replaced
    # 'काला': 'सफेद',
    # 'बुराई': 'अच्छाई',
    # 'शैतान': 'देवता',
    # 'पाप': 'पुण्य',
    # 'अभिशाप': 'आशीर्वाद',
    
    # Common negative words (English) - ALL COMMENTED OUT
    # 'bad': 'good',
    # 'wrong': 'right',
    # 'hate': 'love',
    # 'angry': 'happy',
    # 'sad': 'happy',
    # 'ugly': 'beautiful',
    # 'dirty': 'clean',
    # 'stupid': 'smart',
    # 'idiot': 'friend',
    # 'fool': 'wise',
    # 'crazy': 'calm',
    # 'mad': 'happy',
    # 'kill': 'save',
    # 'death': 'life',
    # 'destroy': 'create',
    # 'break': 'fix',
    # 'hurt': 'help',
    # 'pain': 'joy',
    # 'suffer': 'enjoy',
    # 'cry': 'smile',
    # 'fear': 'courage',  # REMOVED - fear is part of storytelling, should not be replaced
    # 'scared': 'brave',  # REMOVED - scared is part of storytelling, should not be replaced
    # 'weak': 'strong',
    # 'fail': 'succeed',
    # 'lose': 'win',
    # 'enemy': 'friend',
    # 'fight': 'peace',
    # 'war': 'peace',
    # 'violence': 'peace',
    # 'attack': 'protect',
    # 'steal': 'share',
    # 'cheat': 'honest',
    # 'lie': 'truth',
    # 'fake': 'real',
    # 'evil': 'good',
    # 'devil': 'angel',
    # 'hell': 'heaven',
    # 'curse': 'bless',
    # 'damn': 'bless',
    # 'shit': 'stuff',
    # 'damn': 'wow',
    
    # Abusive words (Hindi) - ALL COMMENTED OUT
    # 'बकवास': 'बात',
    # 'बेवकूफ': 'दोस्त',
    # 'मूर्ख': 'साथी',
    # 'गधा': 'दोस्त',
    # 'कुत्ता': 'दोस्त',
    # 'सुअर': 'दोस्त',
    # 'चूतिया': 'दोस्त',
    # 'हरामी': 'दोस्त',
    # 'बदमाश': 'दोस्त',
    # 'लुच्चा': 'दोस्त',
    # 'गुंडा': 'दोस्त',
    # 'दुष्ट': 'दोस्त',
    # 'शैतान': 'दोस्त',
    # 'पाजी': 'दोस्त',
    # 'कमीना': 'दोस्त',
    # 'नालायक': 'योग्य',
    # 'नाकारा': 'सक्षम',
    # 'बेकार': 'उपयोगी',
    # 'गांड': 'पीठ',  # butt -> back (body part, more appropriate)
    # 'गाँड': 'पीठ',
    # 'गांडू': 'दोस्त',
    # 'गाँडू': 'दोस्त',
    # 'गांड में': 'पीठ में',
    # 'गाँड में': 'पीठ में',
    # 'गांड से': 'पीठ से',
    # 'गाँड से': 'पीठ से',
    # 'गांड की': 'पीठ की',
    # 'गाँड की': 'पीठ की',
    # 'गांड का': 'पीठ का',
    # 'गाँड का': 'पीठ का',
    # 'गांड को': 'पीठ को',
    # 'गाँड को': 'पीठ को',
    # 'गांड पर': 'पीठ पर',
    # 'गाँड पर': 'पीठ पर',
    # 'मेरी गांड': 'मेरी पीठ',
    # 'मेरी गाँड': 'मेरी पीठ',
    # 'मेरे गांड': 'मेरी पीठ',
    # 'मेरे गाँड': 'मेरी पीठ',
    # 'गांड में दर्द': 'पीठ में दर्द',
    # 'गाँड में दर्द': 'पीठ में दर्द',
    # 'चूत': 'दोस्त',
    # 'चूतिया': 'दोस्त',
    # 'चूतियापा': 'मजाक',
    # 'भोसड़ी': 'दोस्त',
    # 'भोसड़ा': 'दोस्त',
    # 'भोसड़ीवाला': 'दोस्त',
    # 'मादरचोद': 'दोस्त',
    # 'मादरचोदी': 'दोस्त',
    # 'बहनचोद': 'दोस्त',
    # 'बहनचोदी': 'दोस्त',
    # 'बापचोद': 'दोस्त',
    # 'बापचोदी': 'दोस्त',
    # 'भेंचोद': 'दोस्त',
    # 'भेंचोदी': 'दोस्त',
    # 'लंड': 'दोस्त',
    # 'लंडू': 'दोस्त',
    # 'लंडिया': 'दोस्त',
    # 'लौड़ा': 'दोस्त',
    # 'लौड़े': 'दोस्त',
    # 'लौड़ी': 'दोस्त',
    # 'लौड़ियां': 'दोस्त',
    # 'चोद': 'दोस्त',
    # 'चोदना': 'मिलना',
    # 'चोदा': 'दोस्त',
    # 'चोदी': 'दोस्त',
    # 'चोदू': 'दोस्त',
    # 'चोदे': 'दोस्त',
    # 'चोदेंगे': 'मिलेंगे',
    # 'चोदेंगी': 'मिलेंगी',
    # 'चोदेगा': 'मिलेगा',
    # 'चोदेगी': 'मिलेगी',
    # 'चोद दिया': 'मिल गया',
    # 'चोद दी': 'मिल गई',
    # 'चोद दूंगा': 'मिलूंगा',
    # 'चोद दूंगी': 'मिलूंगी',
    # 'चोद देंगे': 'मिलेंगे',
    # 'चोद देंगी': 'मिलेंगी',
    # 'भेंस': 'दोस्त',
    # 'भेंसी': 'दोस्त',
    # 'भेंसचोद': 'दोस्त',
    # 'भेंसचोदी': 'दोस्त',
    # 'कुतिया': 'दोस्त',
    # 'कुतियापा': 'मजाक',
    # 'कुत्ते': 'दोस्त',
    # 'कुत्ती': 'दोस्त',
    # 'कुत्तों': 'दोस्तों',
    # 'साला': 'दोस्त',
    # 'साले': 'दोस्त',
    # 'साली': 'दोस्त',
    # 'सालियां': 'दोस्त',
    # 'सालू': 'दोस्त',
    # 'हरामखोर': 'दोस्त',
    # 'हरामी': 'दोस्त',
    # 'हरामजादा': 'दोस्त',
    # 'हरामजादी': 'दोस्त',
    # 'हरामजादे': 'दोस्त',
    # 'हरामजादों': 'दोस्तों',
    # 'कमीने': 'दोस्त',
    # 'कमीनी': 'दोस्त',
    # 'कमीनों': 'दोस्तों',
    # 'कमीनियों': 'दोस्तों',
    # 'गंदा': 'साफ',
    # 'गंदी': 'साफ',
    # 'गंदे': 'साफ',
    # 'गंदों': 'साफ',
    # 'गंदी बात': 'साफ बात',
    # 'गंदी बातें': 'साफ बातें',
    # 'गंदगी': 'सफाई',
    # 'गंदा काम': 'साफ काम',
    # 'गंदे काम': 'साफ काम',
    # 'गंदा व्यवहार': 'साफ व्यवहार',
    # 'गंदी हरकत': 'साफ हरकत',
    # 'गंदी हरकतें': 'साफ हरकतें',
    
    # Abusive phrases (Hindi) - ALL COMMENTED OUT
    # 'भाड़ में जाओ': 'शुभकामनाएं',
    # 'चल भाग': 'शुभकामनाएं',
    # 'मर जा': 'जीते रहो',
    # 'भूत बन जा': 'खुश रहो',
    # 'तुझे मार दूंगा': 'तुम्हें मदद करूंगा',
    # 'तू मर गया': 'तुम जीते रहे',
    # 'गांड मार': 'शुभकामनाएं',
    # 'गाँड मार': 'शुभकामनाएं',
    # 'गांड मारो': 'शुभकामनाएं',
    # 'गाँड मारो': 'शुभकामनाएं',
    # 'गांड मारूंगा': 'मदद करूंगा',
    # 'गाँड मारूंगा': 'मदद करूंगा',
    # 'गांड मारूंगी': 'मदद करूंगी',
    # 'गाँड मारूंगी': 'मदद करूंगी',
    # 'गांड मारेंगे': 'मदद करेंगे',
    # 'गाँड मारेंगे': 'मदद करेंगे',
    # 'गांड मारेंगी': 'मदद करेंगी',
    # 'गाँड मारेंगी': 'मदद करेंगी',
    # 'गांड में': 'दोस्तों में',
    # 'गाँड में': 'दोस्तों में',
    # 'गांड से': 'दोस्तों से',
    # 'गाँड से': 'दोस्तों से',
    # 'गांड की': 'दोस्तों की',
    # 'गाँड की': 'दोस्तों की',
    # 'गांड का': 'दोस्तों का',
    # 'गाँड का': 'दोस्तों का',
    # 'गांड को': 'दोस्तों को',
    # 'गाँड को': 'दोस्तों को',
    # 'गांड पर': 'दोस्तों पर',
    # 'गाँड पर': 'दोस्तों पर',
    # 'चूत मार': 'शुभकामनाएं',
    # 'चूत मारो': 'शुभकामनाएं',
    # 'चूत मारूंगा': 'मदद करूंगा',
    # 'चूत मारूंगी': 'मदद करूंगी',
    # 'चूत में': 'दोस्तों में',
    # 'चूत से': 'दोस्तों से',
    # 'चूत की': 'दोस्तों की',
    # 'चूत का': 'दोस्तों का',
    # 'चूत को': 'दोस्तों को',
    # 'चूत पर': 'दोस्तों पर',
    # 'भेंस मार': 'शुभकामनाएं',
    # 'भेंस मारो': 'शुभकामनाएं',
    # 'भेंस मारूंगा': 'मदद करूंगा',
    # 'भेंस मारूंगी': 'मदद करूंगी',
    # 'लंड मार': 'शुभकामनाएं',
    # 'लंड मारो': 'शुभकामनाएं',
    # 'लंड मारूंगा': 'मदद करूंगा',
    # 'लंड मारूंगी': 'मदद करूंगी',
    # 'साला मार': 'शुभकामनाएं',
    # 'साले मार': 'शुभकामनाएं',
    # 'साली मार': 'शुभकामनाएं',
    # 'साला मारो': 'शुभकामनाएं',
    # 'साले मारो': 'शुभकामनाएं',
    # 'साली मारो': 'शुभकामनाएं',
    # 'मादरचोद मार': 'शुभकामनाएं',
    # 'मादरचोद मारो': 'शुभकामनाएं',
    # 'बहनचोद मार': 'शुभकामनाएं',
    # 'बहनचोद मारो': 'शुभकामनाएं',
    # 'बापचोद मार': 'शुभकामनाएं',
    # 'बापचोद मारो': 'शुभकामनाएं',
    # 'भेंचोद मार': 'शुभकामनाएं',
    # 'भेंचोद मारो': 'शुभकामनाएं',
    
    # Abusive words (English) - ALL COMMENTED OUT
    # 'fuck': 'wow',
    # 'shit': 'stuff',
    # 'damn': 'wow',
    # 'hell': 'heaven',
    # 'asshole': 'friend',
    # 'bastard': 'friend',
    # 'bitch': 'friend',
    # 'idiot': 'friend',
    # 'stupid': 'smart',
    # 'dumb': 'smart',
    # 'moron': 'friend',
    # 'retard': 'friend',
    # 'crap': 'stuff',
    # 'piss': 'water',
    # 'pissed': 'upset',
    # 'screw': 'fix',
    # 'screw you': 'good luck',
    # 'fuck off': 'goodbye',
    # 'go to hell': 'have a nice day',
    # 'kill yourself': 'take care',
    # 'die': 'live',
    # 'damn it': 'oh no',
    # 'what the hell': 'what happened',
    # 'what the fuck': 'what happened',
}

# Additional patterns for compound words and phrases
# ALL PHRASE REPLACEMENTS COMMENTED OUT - Word filtering is disabled
PHRASE_REPLACEMENTS = {
    # r'\bबहुत\s+बुरा\b': 'बहुत अच्छा',
    # r'\bबहुत\s+खराब\b': 'बहुत बेहतर',
    # r'\bबहुत\s+गंदा\b': 'बहुत साफ',
    # r'\bबहुत\s+बेकार\b': 'बहुत उपयोगी',
    # r'\bबहुत\s+दुख\b': 'बहुत खुशी',
    # r'\bबहुत\s+पीड़ा\b': 'बहुत सुख',
    # r'\bvery\s+bad\b': 'very good',
    # r'\bvery\s+wrong\b': 'very right',
    # r'\bvery\s+angry\b': 'very happy',
    # r'\bvery\s+sad\b': 'very happy',
    # r'\btoo\s+bad\b': 'that\'s okay',
    # r'\bso\s+bad\b': 'so good',
    # r'\breally\s+bad\b': 'really good',
    # Abusive phrase patterns - ALL COMMENTED OUT
    # r'\bगांड\s+मार\b': 'शुभकामनाएं',
    # r'\bगाँड\s+मार\b': 'शुभकामनाएं',
    # r'\bगांड\s+मारो\b': 'शुभकामनाएं',
    # r'\bगाँड\s+मारो\b': 'शुभकामनाएं',
    # r'\bचूत\s+मार\b': 'शुभकामनाएं',
    # r'\bचूत\s+मारो\b': 'शुभकामनाएं',
    # r'\bलंड\s+मार\b': 'शुभकामनाएं',
    # r'\bलंड\s+मारो\b': 'शुभकामनाएं',
    # r'\bसाला\s+मार\b': 'शुभकामनाएं',
    # r'\bसाले\s+मार\b': 'शुभकामनाएं',
    # r'\bसाली\s+मार\b': 'शुभकामनाएं',
    # r'\bमादरचोद\s+मार\b': 'शुभकामनाएं',
    # r'\bबहनचोद\s+मार\b': 'शुभकामनाएं',
    # r'\bबापचोद\s+मार\b': 'शुभकामनाएं',
    # r'\bभेंचोद\s+मार\b': 'शुभकामनाएं',
}


def filter_negative_words(text):
    """
    Filter and replace negative/abusive words with positive alternatives
    
    NOTE: Word filtering is currently DISABLED (all replacements commented out).
    This function returns text as-is without any replacements.
    
    Args:
        text: Text to filter (can be Hindi or English)
    
    Returns:
        str: Text as-is (no filtering applied since word filtering is disabled)
    """
    if not text:
        return text
    
    # Word filtering is disabled - all dictionaries are empty (commented out)
    # Return text as-is without any replacements
    if not WORD_REPLACEMENTS and not PHRASE_REPLACEMENTS:
        return text
    
    filtered_text = text
    
    # Replace phrases first (longer patterns)
    if PHRASE_REPLACEMENTS:
        for pattern, replacement in PHRASE_REPLACEMENTS.items():
            filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE | re.UNICODE)
    
    # Replace individual words (case-insensitive, whole word match)
    if WORD_REPLACEMENTS:
        for negative_word, positive_word in WORD_REPLACEMENTS.items():
            # Create pattern for whole word match
            # For Hindi: word boundaries might not work, so use word with spaces/punctuation
            pattern = r'\b' + re.escape(negative_word) + r'\b'
            filtered_text = re.sub(pattern, positive_word, filtered_text, flags=re.IGNORECASE | re.UNICODE)
            
            # Also check for word at start/end of line
            pattern_start = r'^' + re.escape(negative_word) + r'(\s|$|[.,!?;:])'
            filtered_text = re.sub(pattern_start, positive_word + r'\1', filtered_text, flags=re.IGNORECASE | re.UNICODE | re.MULTILINE)
            
            pattern_end = r'(\s|^)' + re.escape(negative_word) + r'$'
            filtered_text = re.sub(pattern_end, r'\1' + positive_word, filtered_text, flags=re.IGNORECASE | re.UNICODE | re.MULTILINE)
    
    return filtered_text


def filter_transcript_segments(segments):
    """
    Filter negative words from transcript segments
    
    NOTE: Word filtering is currently DISABLED (all replacements commented out).
    This function returns segments as-is without any replacements.
    
    Args:
        segments: List of segment dicts with 'text' key
    
    Returns:
        list: Segments as-is (no filtering applied since word filtering is disabled)
    """
    if not segments:
        return segments
    
    # Word filtering is disabled - return segments as-is
    if not WORD_REPLACEMENTS and not PHRASE_REPLACEMENTS:
        return segments
    
    filtered_segments = []
    for segment in segments:
        filtered_segment = segment.copy()
        if 'text' in filtered_segment:
            filtered_segment['text'] = filter_negative_words(filtered_segment['text'])
        if 'description' in filtered_segment:
            filtered_segment['description'] = filter_negative_words(filtered_segment['description'])
        filtered_segments.append(filtered_segment)
    
    return filtered_segments

