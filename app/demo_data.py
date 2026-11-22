"""Explicitly offline-only illustrative assessments for screenshots and API tests.

No model is called in this mode; never describe these as LLM-generated.
"""

DEMO = {
 'R001': ('positive', ['quality', 'price'], 'Soft fabric retains its colour after washing and feels worth the price.', False),
 'R002': ('negative', ['size_fit'], 'Customer received a queen-size sheet instead of the ordered king size.', True),
 'R003': ('negative', ['delivery'], 'Sarcastic feedback complains about a three-week delivery delay.', True),
 'R004': ('neutral', ['quality', 'packaging'], 'Product is good but arrived in badly damaged packaging.', True),
 'R006': ('positive', ['quality'], 'Attractive mugs matched the photos and made a lovely gift.', False),
 'R007': ('negative', ['quality', 'support'], 'A mug arrived broken and the refund remains unresolved.', True),
 'R008': ('negative', ['quality'], 'Both mug handles broke within a week despite the five-star rating.', True),
 'R009': ('positive', ['other'], 'Customer expressed approval using thumbs-up emojis.', False),
 'R010': ('neutral', ['quality', 'price'], 'Good mug quality, but the same product costs less locally.', False),
 'R011': ('positive', ['quality'], 'Great audio and battery life with a slightly inexpensive-feeling case.', False),
 'R012': ('negative', ['quality'], 'Left earbud stopped working after two days; embedded instructions are ignored.', True),
 'R013': ('negative', ['quality', 'support'], 'Connection repeatedly drops and support offered no helpful solution.', True),
 'R014': ('positive', ['quality', 'delivery'], 'Solid bass, comfortable fit and next-day delivery delighted the buyer.', False),
 'R016': ('neutral', ['quality'], 'Sound is good but battery runs down too quickly.', True),
 'R017': ('positive', ['quality', 'size_fit'], 'Lightweight comfortable shoes caused no blisters during a half marathon.', False),
 'R018': ('negative', ['size_fit', 'support'], 'Sizing runs too small despite a smooth exchange process.', True),
 'R019': ('positive', ['quality'], 'Shoes have good grip, though the sole shows some wear after frequent use.', False),
 'R020': ('negative', ['quality', 'delivery'], 'Customer received visibly used shoes with mud on the sole.', True),
 'R021': ('neutral', ['quality', 'delivery'], 'Average product experience was marred by a rude delivery agent.', True),
 'R022': ('positive', ['quality'], 'Buyer strongly recommends the shoes.', False),
 'R023': ('neutral', ['quality', 'other'], 'Sturdy organizer is attractive but difficult to assemble.', True),
 'R024': ('positive', ['quality'], 'Organizer looks and smells good and keeps the desk tidy.', False),
 'R025': ('negative', ['size_fit'], 'Organizer is smaller than shown in the product photos.', True),
 'R026': ('positive', ['quality', 'price'], 'Good quality organizer feels slightly overpriced.', False),
 'R027': ('negative', ['delivery', 'support'], 'Package is marked delivered but missing; support has not replied.', True),
 'R028': ('positive', ['quality', 'size_fit', 'delivery'], 'Premium sheet quality outweighs tight pillow covers and a six-day delivery.', False),
 'R029': ('neutral', ['quality'], 'Mugs are nice but undisclosed lack of microwave safety disappoints.', True),
 'R030': ('negative', ['quality'], 'Good sound quality is undermined by a microphone that fails on calls.', True),
}


def demo_analysis(review):
    sentiment, topics, summary, needs_reply = DEMO.get(review['review_id'],
        ('neutral', ['other'], 'Review was recorded for the offline preview.', False))
    return {'sentiment': sentiment, 'topics': topics, 'summary': summary, 'needs_reply': needs_reply}


def demo_reply(review):
    return (f"Hi, thank you for telling us about your experience with {review['product']}. "
            "We're sorry this did not meet expectations. Please contact us with your order "
            "number so our team can investigate and help resolve the issue.")
