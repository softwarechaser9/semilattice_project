# Fixed questions for press release scoring
# 30 questions organized into 5 categories (6 questions each)

PRESS_RELEASE_QUESTIONS = {
    'source_credibility': {
        'display_name': 'Source Credibility',
        'questions': [
            "To what extent is the issuer reputable and trustworthy (1 = no credibility, 6 = highly reputable and trusted)?",
            "How transparent is the organization about its identity (1 = unclear/hidden, 6 = fully transparent)?",
            "How reliable is the organization's history of accuracy and honesty (1 = frequently inaccurate, 6 = consistently accurate)?",
            "How accessible and verifiable is the point of contact provided (1 = no contact/unverifiable, 6 = clear, responsive, and verifiable)?",
            "How credible and relevant are the experts or references cited (1 = none/irrelevant, 6 = highly credible and relevant)?",
            "How appropriate is the timing of the release (1 = appears manipulative/self-serving, 6 = timely and appropriate)?"
        ]
    },
    'accuracy_evidence': {
        'display_name': 'Accuracy & Evidence',
        'questions': [
            "How well are the stated facts supported by verifiable data (1 = unsupported, 6 = fully verifiable with strong data)?",
            "How clearly are statistics sourced and methodologies explained (1 = no sources/methods, 6 = full transparency and clarity)?",
            "How much independent confirmation supports the claims (1 = none, 6 = multiple independent confirmations)?",
            "How authentic and attributable are the included quotes (1 = vague/anonymous, 6 = verifiable and clearly attributable)?",
            "How much solid evidence, rather than vague assertions, is included (1 = only broad claims, 6 = strong, detailed evidence)?",
            "How precise and free from vague or misleading language is the text (1 = very vague/misleading, 6 = precise and transparent)?"
        ]
    },
    'newsworthiness': {
        'display_name': 'Newsworthiness',
        'questions': [
            "How significant is the information to genuine public interest (1 = trivial, 6 = highly significant)?",
            "How timely and relevant is the information to current events (1 = outdated/irrelevant, 6 = extremely timely and relevant)?",
            "How relevant is the announcement to your target audience (1 = not relevant, 6 = highly relevant)?",
            "How new, unique, or impactful is the development (1 = no novelty/impact, 6 = groundbreaking and impactful)?",
            "How substantial are the potential long-term implications (1 = minimal/none, 6 = highly substantial)?",
            "How broad is the scope of the story (1 = very limited, 6 = global or wide-scale significance)?"
        ]
    },
    'bias_intent': {
        'display_name': 'Bias & Intent',
        'questions': [
            "How balanced and informative, rather than purely promotional, is the content (1 = purely promotional, 6 = fully balanced and informative)?",
            "How transparent is it about who benefits from the announcement (1 = no clarity, 6 = full transparency)?",
            "How complete is the information with minimal omissions (1 = key details missing, 6 = comprehensive and complete)?",
            "How neutral and objective is the framing (1 = heavily biased, 6 = entirely neutral and objective)?",
            "How free is the language from emotional manipulation (1 = highly manipulative, 6 = free of manipulation)?",
            "How well does it acknowledge alternative perspectives or counterarguments (1 = none acknowledged, 6 = well represented)?"
        ]
    },
    'practicality_next_steps': {
        'display_name': 'Practicality & Next Steps',
        'questions': [
            "How clear and actionable is the practical information (dates, events, availability) (1 = unclear/unusable, 6 = highly clear and actionable)?",
            "How easy is it to independently verify key claims (1 = not verifiable, 6 = very easy to verify)?",
            "How strong is the availability of supporting materials (reports, images, links) (1 = none provided, 6 = extensive and useful)?",
            "How clear and accessible is the writing for a general audience (1 = confusing/unclear, 6 = very clear and accessible)?",
            "How much further investigation or follow-up is required (1 = major gaps requiring full investigation, 6 = minimal follow-up needed)?",
            "How much does the content read as genuine news rather than PR spin (1 = pure PR spin, 6 = genuine news value)?"
        ]
    }
}

# Helper function to get all questions with their category info
def get_all_questions():
    """Returns a list of all 30 questions with metadata"""
    all_questions = []
    question_number = 1
    
    for category_key, category_data in PRESS_RELEASE_QUESTIONS.items():
        for question in category_data['questions']:
            all_questions.append({
                'number': question_number,
                'category_key': category_key,
                'category_display': category_data['display_name'],
                'question': question,
                'full_question_template': f"Please read the following press release {{press_release_text}} and consider: {question}"
            })
            question_number += 1
    
    return all_questions

# Helper function to format question with press release text
def format_question_with_text(question, press_release_text):
    """Insert press release text into question template"""
    return f"Please read the following press release {press_release_text} and consider: {question}"
