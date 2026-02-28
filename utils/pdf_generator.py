from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


def generate_itinerary_pdf(profile, itinerary_text, weather_context=None,
                           budget_intel=None, cultural_intel=None,
                           health_intel=None, sustainability_intel=None):
    """
    Generates a comprehensive PDF travel dossier with itinerary and deep intelligence.
    
    Args:
        profile: User profile dict with destination, dates, budget, etc.
        itinerary_text: The main itinerary content as text
        weather_context: Optional weather data dict
        budget_intel: Optional budget analysis dict
        cultural_intel: Optional cultural intelligence dict
        health_intel: Optional health advisory dict
        sustainability_intel: Optional eco/sustainability dict
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f6feb'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0d1117'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    body_style = styles['BodyText']
    body_style.fontSize = 11
    body_style.leading = 14
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10,
    )
    
    # Title
    elements.append(Paragraph("WanderTrip Travel Dossier", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Trip Overview Section
    if profile:
        elements.append(Paragraph("Trip Overview", heading_style))
        
        overview_data = []
        if profile.get('destination'):
            overview_data.append(['Destination:', profile['destination']])
        if profile.get('dates'):
            overview_data.append(['Travel Dates:', profile['dates']])
        if profile.get('duration'):
            overview_data.append(['Duration:', f"{profile['duration']} days"])
        if profile.get('group_type'):
            overview_data.append(['Travelers:', profile['group_type']])
        if profile.get('budget'):
            overview_data.append(['Budget:', profile['budget']])
        if profile.get('interests'):
            overview_data.append(['Interests:', profile['interests']])
        
        if overview_data:
            t = Table(overview_data, colWidths=[1.5*inch, 4*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f6f8fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.3 * inch))
    
    # Weather Context
    if weather_context and not weather_context.get('error'):
        elements.append(Paragraph("Current Weather", heading_style))
        weather_text = f"""
        Temperature: {weather_context.get('temperature_c', 'N/A')}°C<br/>
        Condition: {weather_context.get('description', 'N/A')}<br/>
        Status: {weather_context.get('is_day', 'day').capitalize()} time
        """
        elements.append(Paragraph(weather_text, body_style))
        elements.append(Spacer(1, 0.3 * inch))
    
    # Itinerary Content
    elements.append(Paragraph("Your Personalized Itinerary", heading_style))
    
    for line in itinerary_text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line.strip(), body_style))
            elements.append(Spacer(1, 0.1 * inch))
    
    elements.append(Spacer(1, 0.3 * inch))
    
    # === DEEP INTELLIGENCE SECTIONS ===
    
    # Budget Intelligence
    if budget_intel and not budget_intel.get('error'):
        elements.append(Paragraph("Budget Intelligence", heading_style))
        
        feasibility = budget_intel.get('feasibility', 'N/A')
        daily = budget_intel.get('daily_needed', 'N/A')
        elements.append(Paragraph(
            f"<b>Feasibility:</b> {feasibility} | <b>Est. Daily Cost:</b> {daily}",
            body_style
        ))
        
        breakdown = budget_intel.get('breakdown', {})
        if breakdown:
            budget_data = []
            for category, cost in breakdown.items():
                budget_data.append([category.capitalize(), str(cost)])
            
            if budget_data:
                bt = Table(budget_data, colWidths=[2*inch, 3.5*inch])
                bt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                elements.append(bt)
        
        tips = budget_intel.get('tips', [])
        if tips:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("Saving Tips:", subheading_style))
            for tip in tips[:5]:
                elements.append(Paragraph(f"• {tip}", bullet_style))
        
        elements.append(Spacer(1, 0.3 * inch))
    
    # Cultural Intelligence
    if cultural_intel and not cultural_intel.get('error'):
        elements.append(Paragraph("Cultural Guide", heading_style))
        
        dos = cultural_intel.get('etiquette_dos', [])
        if dos:
            elements.append(Paragraph("Do's:", subheading_style))
            for item in dos[:5]:
                elements.append(Paragraph(f"• {item}", bullet_style))
        
        donts = cultural_intel.get('etiquette_donts', [])
        if donts:
            elements.append(Paragraph("Don'ts:", subheading_style))
            for item in donts[:5]:
                elements.append(Paragraph(f"• {item}", bullet_style))
        
        tipping = cultural_intel.get('tipping_guide')
        if tipping:
            elements.append(Paragraph(f"<b>Tipping:</b> {tipping}", body_style))
        
        dress = cultural_intel.get('dress_code')
        if dress:
            elements.append(Paragraph(f"<b>Dress Code:</b> {dress}", body_style))
        
        phrases = cultural_intel.get('language_tips', [])
        if phrases:
            elements.append(Paragraph("Key Phrases:", subheading_style))
            phrase_data = [['English', 'Local', 'Pronunciation']]
            for p in phrases[:6]:
                phrase_data.append([
                    str(p.get('phrase', '')),
                    str(p.get('local', '')),
                    str(p.get('pronunciation', ''))
                ])
            pt = Table(phrase_data, colWidths=[1.5*inch, 2*inch, 2*inch])
            pt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(pt)
        
        elements.append(Spacer(1, 0.3 * inch))
    
    # Health Advisory
    if health_intel and not health_intel.get('error'):
        elements.append(Paragraph("Health Advisory", heading_style))
        
        water = health_intel.get('water_safety')
        if water:
            elements.append(Paragraph(f"<b>Water Safety:</b> {water}", body_style))
        
        vaccinations = health_intel.get('vaccinations', [])
        if vaccinations:
            elements.append(Paragraph("Recommended Vaccinations:", subheading_style))
            for v in vaccinations[:6]:
                elements.append(Paragraph(f"• {v}", bullet_style))
        
        emergency = health_intel.get('emergency_numbers')
        if emergency:
            elements.append(Paragraph(f"<b>Emergency:</b> {emergency}", body_style))
        
        elements.append(Spacer(1, 0.3 * inch))
    
    # Sustainability
    if sustainability_intel and not sustainability_intel.get('error'):
        elements.append(Paragraph("Eco & Sustainability", heading_style))
        
        carbon = sustainability_intel.get('carbon_footprint_est')
        if carbon:
            elements.append(Paragraph(f"<b>Carbon Footprint Est.:</b> {carbon}", body_style))
        
        green_rating = sustainability_intel.get('green_rating')
        if green_rating:
            elements.append(Paragraph(f"<b>Green Rating:</b> {green_rating}", body_style))
        
        eco_tips = sustainability_intel.get('tips', sustainability_intel.get('eco_tips', []))
        if eco_tips:
            elements.append(Paragraph("Eco Tips:", subheading_style))
            for tip in eco_tips[:4]:
                elements.append(Paragraph(f"• {tip}", bullet_style))
        
        elements.append(Spacer(1, 0.3 * inch))
    
    # Footer
    elements.append(Spacer(1, 0.5 * inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Generated by WanderTrip - Your AI Travel Copilot", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_simple_pdf(title, content):
    """
    Generates a simple PDF with just title and content.
    
    Args:
        title: PDF title
        content: Main content text
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 0.3 * inch))
    
    for line in content.split('\n'):
        if line.strip():
            elements.append(Paragraph(line.strip(), styles['BodyText']))
            elements.append(Spacer(1, 0.1 * inch))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
