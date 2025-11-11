"""
Hotel Chatbot Knowledge Manager - Main Streamlit App
"""

import streamlit as st
import os
import tempfile
from datetime import datetime
import pandas as pd

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Hotel Knowledge Base Manager",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check if running with full setup
try:
    from hotel_scraper import scrape_and_ingest_hotel_website, process_uploaded_document
    from real_hotel_scraper import RealHotelScraper, create_knowledge_chunks
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False

# Session state initialization
if 'hotel_id' not in st.session_state:
    st.session_state.hotel_id = None
if 'project_id' not in st.session_state:
    st.session_state.project_id = os.getenv('GCP_PROJECT_ID', '')
if 'scraped_pages' not in st.session_state:
    st.session_state.scraped_pages = 0
if 'uploaded_docs' not in st.session_state:
    st.session_state.uploaded_docs = 0
if 'last_scrape' not in st.session_state:
    st.session_state.last_scrape = None


def main():
    # Header
    st.title("🏨 Hotel Chatbot Knowledge Manager")
    st.markdown("""
    Manage your hotel's AI chatbot by scraping your website or uploading documents.
    Your chatbot will use this information to answer customer questions with hotel-specific details.
    """)
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Hotel ID input
        hotel_id = st.text_input(
            "Hotel ID",
            value=st.session_state.hotel_id or "",
            help="Your unique hotel identifier (e.g., 'grand_plaza_001')",
            placeholder="Enter hotel ID"
        )
        
        if hotel_id:
            st.session_state.hotel_id = hotel_id
            st.success(f"✅ Hotel: {hotel_id}")
        else:
            st.info("👆 Enter your Hotel ID to get started")
        
        # Project ID
        project_id = st.text_input(
            "GCP Project ID",
            value=st.session_state.project_id,
            help="Your Google Cloud Project ID for Vertex AI",
            placeholder="your-gcp-project"
        )
        st.session_state.project_id = project_id
        
        st.divider()
        
        # Status metrics
        st.subheader("📊 Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pages", st.session_state.scraped_pages)
        with col2:
            st.metric("Docs", st.session_state.uploaded_docs)
        
        if st.session_state.last_scrape:
            st.caption(f"Last updated: {st.session_state.last_scrape}")
        
        if not MODULES_AVAILABLE:
            st.error("🔧 Setup Required")
            st.markdown("""
            Install dependencies:
            ```bash
            pip install -r requirements.txt
            ```
            """)
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Website Scraping", 
        "📄 Upload Documents", 
        "💬 Test Chatbot",
        "📚 Help & Setup"
    ])
    
    # ========================================================================
    # TAB 1: Website Scraping
    # ========================================================================
    with tab1:
        st.header("Website Scraping")
        st.markdown("Automatically extract content from your hotel website")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            website_url = st.text_input(
                "Hotel Website URL",
                placeholder="https://www.your-hotel.com",
                help="Full URL including https://"
            )
            
            max_pages = st.slider(
                "Maximum Pages to Scrape",
                min_value=5,
                max_value=50,
                value=20,
                step=5,
                help="More pages = more comprehensive knowledge base"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                delay = st.number_input(
                    "Delay (seconds)",
                    min_value=1.0,
                    max_value=5.0,
                    value=2.0,
                    step=0.5,
                    help="Delay between page requests (be polite!)"
                )
        
        with col2:
            st.info("""
            ### 📋 What Gets Scraped
            ✅ Room descriptions  
            ✅ Pricing information  
            ✅ Amenities & facilities  
            ✅ Restaurant menus  
            ✅ Hotel policies  
            ✅ Contact information  
            ✅ About/history pages  
            
            **Skips:**
            ❌ Login/admin pages  
            ❌ Shopping carts  
            ❌ External links  
            """)
        
        # Scrape button
        can_scrape = st.session_state.hotel_id and website_url and MODULES_AVAILABLE
        
        if st.button(
            "🔍 Start Scraping", 
            type="primary",
            disabled=not can_scrape,
            use_container_width=True
        ):
            if not MODULES_AVAILABLE:
                st.error("❌ Required modules not installed. Run: pip install -r requirements.txt")
                return
            
            with st.spinner("🔄 Scraping website... This may take a few minutes"):
                progress_bar = st.progress(0)
                status = st.empty()
                
                try:
                    status.text("🔍 Starting crawl...")
                    progress_bar.progress(10)
                    
                    # Real scraping
                    scraper = RealHotelScraper(max_pages=max_pages, delay=delay)
                    scraped_data = scraper.scrape_hotel_website(website_url)
                    
                    progress_bar.progress(50)
                    status.text("📦 Creating knowledge chunks...")
                    
                    # Create chunks
                    chunks = create_knowledge_chunks(scraped_data)
                    
                    progress_bar.progress(80)
                    status.text("💾 Saving to knowledge base...")
                    
                    # Save results
                    scraper.save_results(scraped_data, f"scraped_{st.session_state.hotel_id}.json")
                    
                    progress_bar.progress(100)
                    status.empty()
                    
                    # Update session state
                    st.session_state.scraped_pages = scraped_data['pages_scraped']
                    st.session_state.last_scrape = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    st.success(f"✅ Successfully scraped {scraped_data['pages_scraped']} pages and created {len(chunks)} knowledge chunks!")
                    st.balloons()
                    
                    # Show summary
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Pages", scraped_data['pages_scraped'])
                    col2.metric("Chunks", len(chunks))
                    col3.metric("Words", f"{scraped_data['metadata']['total_words']:,}")
                    
                    # Show page types
                    st.subheader("Content Breakdown")
                    page_types_df = pd.DataFrame(
                        scraped_data['metadata']['page_types'].items(),
                        columns=['Page Type', 'Count']
                    )
                    st.bar_chart(page_types_df.set_index('Page Type'))
                
                except Exception as e:
                    progress_bar.empty()
                    status.empty()
                    st.error(f"❌ Scraping failed: {str(e)}")
                    st.info("💡 Tips: Check URL format, verify site is accessible, try reducing max pages")
        
        st.divider()
        
        # Preview feature
        with st.expander("👁️ Preview Content Before Scraping"):
            st.markdown("Quick preview of what will be scraped (first 3 pages only)")
            
            if st.button("Generate Preview") and website_url and MODULES_AVAILABLE:
                with st.spinner("Fetching preview..."):
                    try:
                        scraper = RealHotelScraper(max_pages=3, delay=1.0)
                        preview_data = scraper.scrape_hotel_website(website_url)
                        
                        if preview_data['pages']:
                            for i, page in enumerate(preview_data['pages'], 1):
                                st.markdown(f"**Page {i}: {page['title']}**")
                                st.caption(f"Type: {page['page_type']} | Words: {page['word_count']}")
                                with st.expander("View content"):
                                    st.text(page['content'][:500] + "...")
                        else:
                            st.warning("No content found in preview")
                    except Exception as e:
                        st.error(f"Preview failed: {str(e)}")
    
    # ========================================================================
    # TAB 2: Document Upload
    # ========================================================================
    with tab2:
        st.header("Upload Documents")
        st.markdown("Add PDFs or Excel files to supplement your scraped content")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=['pdf', 'xlsx', 'xls'],
            accept_multiple_files=True,
            help="Supported: PDF, Excel (.xlsx, .xls). Max 10MB per file recommended."
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) ready to upload")
            
            # Preview files
            for file in uploaded_files:
                cols = st.columns([4, 1, 1])
                cols[0].text(f"📄 {file.name}")
                cols[1].text(f"{file.size/1024:.1f}KB")
                cols[2].text(file.type.split('/')[-1].upper())
            
            st.divider()
            
            # Optional description
            description = st.text_area(
                "Description (optional)",
                placeholder="e.g., 'Updated winter menu 2025' or 'New room rates'",
                max_chars=200
            )
            
            # Upload button
            if st.button(
                "📤 Upload & Process", 
                type="primary",
                disabled=not (st.session_state.hotel_id and MODULES_AVAILABLE),
                use_container_width=True
            ):
                if not MODULES_AVAILABLE:
                    st.error("Required modules not available")
                    return
                
                progress = st.progress(0)
                
                for idx, file in enumerate(uploaded_files):
                    try:
                        progress.progress(int((idx / len(uploaded_files)) * 100))
                        
                        # Save temp file
                        with tempfile.NamedTemporaryFile(
                            delete=False, 
                            suffix=os.path.splitext(file.name)[1]
                        ) as tmp:
                            tmp.write(file.getvalue())
                            tmp_path = tmp.name
                        
                        # Process
                        success = process_uploaded_document(
                            hotel_id=st.session_state.hotel_id,
                            file_path=tmp_path,
                            project_id=st.session_state.project_id
                        )
                        
                        os.unlink(tmp_path)
                        
                        if success:
                            st.success(f"✅ {file.name} processed successfully!")
                            st.session_state.uploaded_docs += 1
                        else:
                            st.error(f"❌ Failed to process {file.name}")
                    
                    except Exception as e:
                        st.error(f"❌ {file.name}: {str(e)}")
                
                progress.progress(100)
                progress.empty()
                st.balloons()
        
        # Tips
        with st.expander("💡 Upload Best Practices"):
            st.markdown("""
            **For Best Results:**
            
            ✅ **PDFs**: Use text-based PDFs (not scanned images)  
            ✅ **Excel**: Clear headers, organized data, one topic per sheet  
            ✅ **File Size**: Keep under 10MB  
            ✅ **Updates**: Replace old files with new versions regularly  
            
            **Good Examples:**
            - Restaurant menu (PDF)
            - Room rates and packages (Excel)
            - Hotel policies (PDF)
            - Amenities list (PDF/Excel)
            - Event spaces info (PDF)
            
            **What Happens:**
            1. Text is extracted from your files
            2. Content is broken into chunks
            3. Chunks are embedded and indexed
            4. Chatbot can now answer questions using this info!
            """)
    
    # ========================================================================
    # TAB 3: Test Chatbot
    # ========================================================================
    with tab3:
        st.header("Test Your Chatbot")
        st.markdown("Try out sample queries to see how your chatbot will respond")
        
        if not st.session_state.hotel_id:
            st.warning("⚠️ Please enter Hotel ID in the sidebar first")
        elif st.session_state.scraped_pages == 0 and st.session_state.uploaded_docs == 0:
            st.info("ℹ️ Scrape your website or upload documents first to enable testing")
        else:
            # Sample queries
            st.subheader("Quick Test Questions:")
            
            sample_queries = [
                "What time is check-in?",
                "What amenities do you offer?",
                "Tell me about your restaurant",
                "What room types are available?",
                "Do you allow pets?",
                "What's your cancellation policy?"
            ]
            
            cols = st.columns(3)
            for idx, query in enumerate(sample_queries):
                if cols[idx % 3].button(query, use_container_width=True):
                    st.session_state.test_query = query
            
            st.divider()
            
            # Chat interface
            user_query = st.text_input(
                "Ask a question:",
                value=st.session_state.get('test_query', ''),
                placeholder="e.g., Do you have a pool?"
            )
            
            if st.button("💬 Ask Chatbot", type="primary", use_container_width=True) and user_query:
                with st.spinner("🤔 Thinking..."):
                    # In production, this would call the actual RAG chatbot
                    st.info(f"""
                    **Demo Response for: "{user_query}"**
                    
                    Once your knowledge base is fully set up with vector embeddings, 
                    the chatbot will:
                    
                    1. 🔍 Search your indexed content for relevant information
                    2. 📚 Retrieve the most relevant chunks (using semantic similarity)
                    3. 🤖 Generate a natural response using Vertex AI with that context
                    4. ✅ Provide accurate, hotel-specific answers
                    
                    **Next Steps:**
                    - Complete the vector DB setup (PostgreSQL + pgvector)
                    - Configure Vertex AI embeddings
                    - Test with the full RAG pipeline
                    
                    Your scraped content is ready and waiting!
                    """)
            
            st.divider()
            
            # Integration info
            with st.expander("🔌 Integration Options"):
                st.markdown("""
                ### WhatsApp Integration
                1. Set up WhatsApp Business API account
                2. Configure webhook endpoint
                3. Connect to your chatbot API
                4. Customers can message your hotel number!
                
                ### Website Widget
                Add this code to your hotel website:
                ```html
                <script src="https://cdn.hotelchat.com/widget.js"
                        data-hotel-id="YOUR_HOTEL_ID"
                        data-api-key="YOUR_API_KEY">
                </script>
                ```
                
                ### API Endpoint
                ```python
                POST /api/v1/chat/message
                {
                  "hotel_id": "your_hotel_id",
                  "message": "Customer question here"
                }
                ```
                """)
    
    # ========================================================================
    # TAB 4: Help & Setup
    # ========================================================================
    with tab4:
        st.header("📚 Help & Setup Guide")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚀 Quick Start")
            st.markdown("""
            **Step 1: Configuration**
            - Enter your Hotel ID (sidebar)
            - Add GCP Project ID (sidebar)
            
            **Step 2: Add Knowledge**
            - Option A: Scrape your website
            - Option B: Upload PDF/Excel files
            - Or do both!
            
            **Step 3: Test**
            - Try sample questions
            - Verify responses are accurate
            
            **Step 4: Deploy**
            - Set up vector database
            - Configure Vertex AI
            - Integrate with WhatsApp/website
            """)
            
            st.subheader("🔧 Technical Setup")
            st.markdown("""
            **Required Services:**
            
            1. **PostgreSQL with pgvector**
               ```sql
               CREATE EXTENSION vector;
               ```
            
            2. **Vertex AI** (Embeddings + LLM)
               - textembedding-gecko@003
               - chat-bison@002
            
            3. **Redis** (optional, for caching)
            
            4. **Cloud Run** (for deployment)
            
            See full setup guide in repository README.
            """)
        
        with col2:
            st.subheader("❓ Troubleshooting")
            st.markdown("""
            **Scraping Issues:**
            - ✅ Check URL includes https://
            - ✅ Some sites block bots (try uploading instead)
            - ✅ Reduce max pages if timing out
            - ✅ Increase delay if getting errors
            
            **Upload Errors:**
            - ✅ PDF must be text-based (not scanned)
            - ✅ Keep files under 10MB
            - ✅ Excel needs proper formatting
            
            **Chatbot Not Accurate:**
            - ✅ Scrape more pages
            - ✅ Upload detailed documents
            - ✅ Update content regularly
            - ✅ Check vector DB is configured
            """)
            
            st.subheader("💰 Cost Estimate")
            st.info("""
            **Estimated Monthly Costs:**
            
            - Cloud SQL: ~$50
            - Redis: ~$30
            - Cloud Run: ~$20
            - Vertex AI: ~$50-100 (usage-based)
            - Storage: ~$5
            
            **Total: ~$155-205/month**
            
            Scales with usage!
            """)
            
            st.subheader("📧 Support")
            st.markdown("""
            **Need Help?**
            
            - 📖 [Documentation](https://github.com/your-repo)
            - 💬 [Community Forum](https://github.com/your-repo/discussions)
            - 🐛 [Report Issue](https://github.com/your-repo/issues)
            """)
    
    # Footer
    st.divider()
    st.caption("Hotel Chatbot Manager v1.0 | Built with Streamlit & Vertex AI | Open Source")


if __name__ == "__main__":
    main()
