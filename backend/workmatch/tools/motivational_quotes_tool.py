import random
from typing import Optional

QUOTES_WITH_CONTEXT = [
    {
        "quote": "Your future isn’t fixed — it’s built one step at a time.",
        "author": "Unknown",
        "explanation": "Every meaningful journey starts with a single decision to move forward. Your career is not predefined — each small action today shapes the future you want tomorrow."
    },
    {
        "quote": "Success is the sum of small efforts, repeated day in and day out.",
        "author": "Robert Collier",
        "explanation": "Consistency is the true engine of change. Every application you submit, every skill you learn, builds momentum toward your breakthrough moment."
    },
    {
        "quote": "Believe you can and you’re halfway there.",
        "author": "Theodore Roosevelt",
        "explanation": "Confidence can turn hesitation into action. If you trust your potential, you'll naturally take the steps needed to bring it to life."
    },
    {
        "quote": "Do not wait for the perfect moment — take the moment and make it perfect.",
        "author": "Unknown",
        "explanation": "There's no such thing as the 'right time.' The best opportunities often come when you start where you are, with what you have."
    },
    {
        "quote": "Don’t watch the clock; do what it does. Keep going.",
        "author": "Sam Levenson",
        "explanation": "Time keeps moving — and so can you. Each hour spent making progress adds up to something meaningful."
    },
    {
        "quote": "It does not matter how slowly you go as long as you do not stop.",
        "author": "Confucius",
        "explanation": "Your pace doesn’t define your success — your persistence does. Keep applying, learning, growing."
    },
    {
        "quote": "What would life be if we had no courage to attempt anything?",
        "author": "Vincent Van Gogh",
        "explanation": "Your goals may feel uncertain, but starting is the bravest and most powerful thing you can do."
    },
    {
        "quote": "It always seems impossible until it’s done.",
        "author": "Nelson Mandela",
        "explanation": "That next step may feel out of reach now, but many achievements begin with doubt — and end in transformation."
    },
    {
        "quote": "The best way to predict the future is to invent it.",
        "author": "Alan Kay",
        "explanation": "You're not just searching for a job — you're designing the career you want."
    },
    {
        "quote": "Success is a lousy teacher. It seduces smart people into thinking they can’t lose.",
        "author": "Bill Gates",
        "explanation": "Stay curious and willing to learn — especially when things are going well. Growth comes from humility."
    },
    {
        "quote": "Innovation distinguishes between a leader and a follower.",
        "author": "Steve Jobs",
        "explanation": "In your career, thinking differently can open doors that others never imagined."
    },
    {
        "quote": "Sometimes it is the people no one can imagine anything of who do the things no one can imagine.",
        "author": "Alan Turing",
        "explanation": "No matter your background or starting point, you can become the exception."
    },
    {
        "quote": "Programs must be written for people to read, and only incidentally for machines to execute.",
        "author": "Harold Abelson",
        "explanation": "Clear communication is as valuable as technical skill — especially in a collaborative world."
    },
    {
        "quote": "Any sufficiently advanced technology is indistinguishable from magic.",
        "author": "Arthur C. Clarke",
        "explanation": "Tech can feel overwhelming — but every expert started out as a beginner in awe."
    },
    {
        "quote": "The most effective debugging tool is still careful thought, coupled with judiciously placed print statements.",
        "author": "Brian Kernighan",
        "explanation": "Simple, thoughtful strategies often outshine complexity — in code and in life."
    },
    {
        "quote": "The real problem is not whether machines think but whether men do.",
        "author": "B.F. Skinner",
        "explanation": "Your mindset shapes what you create and contribute. Be thoughtful, intentional, and human."
    },
    {
        "quote": "Science is what we understand well enough to explain to a computer. Art is everything else we do.",
        "author": "Donald Knuth",
        "explanation": "Even in technical fields, creativity and intuition drive the most meaningful progress."
    },
]

async def get_motivational_quote(with_explanation: bool = True) -> str:
    """
    Returns a random motivational or tech quote, with explanation by default.
    """
    quote_obj = random.choice(QUOTES_WITH_CONTEXT)
    quote_line = f'*“{quote_obj["quote"]}” — {quote_obj["author"]}*'
    if with_explanation:
        return f"{quote_line}\n\n> {quote_obj['explanation']}"
    return quote_line
