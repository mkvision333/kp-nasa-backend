# app/core/rashiphal/aries.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    # Aries birth sign; Moon transits across 12 signs.
    return {
        "Aries": TransitNote(
            moon_sign="Aries",
            house=1,
            headline="High Energy, Fresh Starts",
            sections={
                "Effects": (
                    "Your mind moves quickly today. You feel motivated to start new tasks, take initiative, "
                    "and lead from the front. Good day for planning, pitching ideas, and beginning something "
                    "you postponed."
                ),
                "Finance": (
                    "Spending on yourself can rise (personal upgrades, tools, learning). "
                    "Short-term opportunities may give quick gains, but avoid impulsive purchases."
                ),
                "Health": (
                    "Headache or eye strain is possible. Drink more water, reduce screen strain, "
                    "and avoid rushing decisions when emotions spike."
                ),
                "Tips": (
                    "Channel the speed into one priority. Finish one important task before jumping to the next."
                ),
            },
            remedy="Remember Lord Subrahmanya (Kartikeya) for calm focus and inner steadiness.",
        ),

        "Taurus": TransitNote(
            moon_sign="Taurus",
            house=2,
            headline="Sweet Speech, Family & Money Flow",
            sections={
                "Effects": (
                    "Your speech becomes softer and more persuasive. Family time, food, and comfort take priority. "
                    "You can settle family matters peacefully."
                ),
                "Finance": (
                    "Cash flow improves. Old dues may be recovered. Chances of buying valuables or gold increase, "
                    "but keep moderation."
                ),
                "Communication": (
                    "You speak clearly and directly. People are more likely to agree with your proposals."
                ),
                "Caution": "Overeating can cause discomfort. Keep food under control.",
            },
        ),

        "Gemini": TransitNote(
            moon_sign="Gemini",
            house=3,
            headline="Short Trips, Learning & Networking",
            sections={
                "Effects": (
                    "Short travels and active communication are highlighted. Bonds with siblings strengthen. "
                    "Curiosity increases; you may learn new skills or explore new information."
                ),
                "Finance": (
                    "Those in communication, marketing, teaching, writing, or sales can gain financially. "
                    "You may spend on promotions or outreach."
                ),
                "Habits": "Build a reading/writing habit today. Mental sharpness improves.",
            },
            remedy="Vishnu Sahasranama chanting is supportive for clarity and steady progress.",
        ),

        "Cancer": TransitNote(
            moon_sign="Cancer",
            house=4,
            headline="Home, Mother & Inner Peace",
            sections={
                "Effects": (
                    "Home matters gain importance. You seek emotional comfort and calm. "
                    "Support from mother/family can increase. Vehicle or property comfort may improve."
                ),
                "Finance": (
                    "Good time to plan home-related spending: appliances, repairs, or real-estate decisions "
                    "with careful evaluation."
                ),
                "Health": (
                    "Be cautious with chest/cold-related sensitivity. Avoid very cold foods and keep breathing relaxed."
                ),
                "Learning": "Practice emotional control and respond slowly rather than react quickly.",
            },
        ),

        "Leo": TransitNote(
            moon_sign="Leo",
            house=5,
            headline="Creativity Peak, Joy & Recognition",
            sections={
                "Effects": (
                    "For Aries natives, this transit feels like a mini-rajayoga. Creativity rises, "
                    "confidence increases, and children/creative outcomes bring joy."
                ),
                "Finance": (
                    "Speculation or markets can give profits if you act with discipline. "
                    "Luxury spending may increase—keep a budget."
                ),
                "Communication": "You speak with confidence; appreciation in meetings or public spaces is possible.",
            },
            remedy="Do Surya Namaskar to increase vitality and positive confidence.",
        ),

        "Virgo": TransitNote(
            moon_sign="Virgo",
            house=6,
            headline="Work Pressure, Competition & Wins",
            sections={
                "Effects": (
                    "Workload increases, but you can defeat obstacles and competitors. "
                    "Legal/official matters may become favorable if you stay organized."
                ),
                "Finance": (
                    "Good day to clear debts and track expenses. Avoid unnecessary spending and keep accounts clean."
                ),
                "Health": (
                    "Digestive sensitivity is possible. Eat light, keep routine, and avoid skipping meals."
                ),
                "Skills": "Focus on improving practical skills; productivity gains will follow.",
            },
        ),

        "Libra": TransitNote(
            moon_sign="Libra",
            house=7,
            headline="Partnerships, PR & Agreements",
            sections={
                "Effects": (
                    "Business partnerships can perform well. Relationship harmony increases when you listen well. "
                    "Public relations improve; negotiations go smoother."
                ),
                "Finance": (
                    "Income may rise through others’ support, collaborations, or new contracts."
                ),
                "Communication": (
                    "You speak with diplomacy and respect. Compromise brings better outcomes."
                ),
            },
            remedy="Worship Goddess Lakshmi for harmony and auspicious agreements.",
        ),

        "Scorpio": TransitNote(
            moon_sign="Scorpio",
            house=8,
            headline="Unexpected Turns, Deep Thinking",
            sections={
                "Effects": (
                    "Mental restlessness can occur. Sudden changes may happen, pushing you to adapt. "
                    "Interest in secrets, research, or hidden matters increases."
                ),
                "Finance": (
                    "Sudden money via insurance, refunds, or unexpected sources is possible. "
                    "Avoid risky investments today."
                ),
                "Health": (
                    "Drive carefully and stay focused. Avoid overthinking; protect your sleep quality."
                ),
                "Habits": "Meditation helps. Stay away from unnecessary fears and dramatic assumptions.",
            },
        ),

        "Sagittarius": TransitNote(
            moon_sign="Sagittarius",
            house=9,
            headline="Luck, Travel & Blessings",
            sections={
                "Effects": (
                    "Fortune supports you. Long travel, spiritual visits, or guidance from elders is highlighted. "
                    "Your optimism returns and direction becomes clearer."
                ),
                "Finance": (
                    "Spending on dharma/charity or learning can happen. Foreign links can bring benefits."
                ),
                "Communication": (
                    "You speak ethically and inspire others. Your advice may be valued more today."
                ),
                "Learning": "Good day to focus on higher education, philosophy, or meaningful study.",
            },
        ),

        "Capricorn": TransitNote(
            moon_sign="Capricorn",
            house=10,
            headline="Career Growth & Status",
            sections={
                "Effects": (
                    "Strong career day. Recognition from seniors or authority figures is possible. "
                    "Your public image improves when you act responsibly."
                ),
                "Finance": (
                    "Income can increase through profession. Favorable time to plan long-term investments carefully."
                ),
                "Habits": "Increase discipline. Avoid laziness and keep consistent effort.",
            },
            remedy="Offer abhishekam or prayer to Lord Shiva to remove career obstacles.",
        ),

        "Aquarius": TransitNote(
            moon_sign="Aquarius",
            house=11,
            headline="Gains, Networks & Fulfillment",
            sections={
                "Effects": (
                    "Wishes move toward fulfillment. Friends support you, and beneficial news can arrive. "
                    "Teamwork brings opportunities."
                ),
                "Finance": (
                    "Multiple income routes may open. Networking can directly convert into money or leads."
                ),
                "Communication": (
                    "You speak with social awareness and do well in group discussions."
                ),
                "Health": "Watch for leg/ankle strain; take short walks and stretch.",
            },
        ),

        "Pisces": TransitNote(
            moon_sign="Pisces",
            house=12,
            headline="Expenses, Solitude & Spiritual Mood",
            sections={
                "Effects": (
                    "Expenses rise. You may prefer solitude, reflection, and spiritual thinking. "
                    "Good for closing tasks, releasing clutter, and resting the mind."
                ),
                "Finance": (
                    "Hospital/charity/foreign-related spending is possible. Foreign efforts may bring results, "
                    "but manage cash carefully."
                ),
                "Health": (
                    "Prioritize sleep and mental calm. Yoga, breathing, and low stimulation help."
                ),
                "Learning": "Learn forgiveness and letting go; it reduces stress and improves clarity.",
            },
        ),
    }
