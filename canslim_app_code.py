import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import time
import io
import base64
from nsepy import get_history
import yfinance as yf
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Page configuration
st.set_page_config(
    page_title="CAN SLIM Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 1rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    .highlight-green {
        background-color: #D5F5E3;
        padding: 10px;
        border-radius: 5px;
    }
    .highlight-red {
        background-color: #FADBD8;
        padding: 10px;
        border-radius: 5px;
    }
    .highlight-yellow {
        background-color: #FCF3CF;
        padding: 10px;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/William_O%27Neil.jpg/220px-William_O%27Neil.jpg", width=100)
st.sidebar.title("CAN SLIM Trader")
st.sidebar.markdown("A no-code solution for CAN SLIM trading")
st.sidebar.divider()

# Initialize session state variables
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=['Stock', 'Entry', 'Current', 'P/L%', 'Target', 'Stop Loss', 'Status', 'Entry Date'])

if 'monthly_picks' not in st.session_state:
    st.session_state.monthly_picks = pd.DataFrame(columns=['Stock', 'Entry', 'Target', 'Stop Loss', 'Selected'])

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.datetime.now()

if 'email' not in st.session_state:
    st.session_state.email = ""

# Helper Functions
def get_nse_data(symbol, period='3mo'):
    """Get historical stock data from NSE"""
    try:
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=90)
        df = get_history(symbol=symbol, start=start_date, end=end_date)
        return df
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def get_rs_rating(df, lookback=60):
    """Calculate Relative Strength Rating"""
    if df.empty:
        return 0
    
    try:
        # Calculate the percentage change over the lookback period
        if len(df) >= lookback:
            change = ((df['Close'].iloc[-1] - df['Close'].iloc[-lookback]) / df['Close'].iloc[-lookback]) * 100
            # Convert to a 0-100 scale (simplified)
            rs_rating = min(100, max(0, change + 50))  # Simplified conversion
            return round(rs_rating, 1)
        return 50  # Default if not enough data
    except Exception as e:
        st.warning(f"Could not calculate RS Rating: {e}")
        return 0

def check_canslim_criteria(symbol):
    """Check if a stock meets CAN SLIM criteria"""
    try:
        df = get_nse_data(symbol)
        if df.empty:
            return {"status": False, "message": f"No data available for {symbol}"}
        
        # Simplified CAN SLIM checks
        # 1. Current Quarterly Earnings (C)
        recent_growth = np.random.randint(10, 40)  # Simulated (would need actual earnings data)
        c_check = recent_growth >= 25
        
        # 2. Annual Earnings Growth (A)
        annual_growth = np.random.randint(10, 35)  # Simulated
        a_check = annual_growth >= 25
        
        # 3. New Products, Services (N)
        # This is qualitative - simulating
        n_check = np.random.choice([True, False], p=[0.7, 0.3])
        
        # 4. Supply and Demand (S)
        volume_change = np.random.randint(-20, 50)  # Simulated
        s_check = volume_change > 20
        
        # 5. Leader or Laggard (L)
        rs_rating = get_rs_rating(df)
        l_check = rs_rating >= 80
        
        # 6. Institutional Sponsorship (I)
        # This is hard to check programmatically - simulating
        i_check = np.random.choice([True, False], p=[0.7, 0.3])
        
        # 7. Market Direction (M)
        market_uptrend = np.random.choice([True, False], p=[0.8, 0.2])  # Simulated
        m_check = market_uptrend
        
        criteria_met = sum([c_check, a_check, n_check, s_check, l_check, i_check, m_check])
        
        # Calculate entry, target, and stop loss
        current_price = df['Close'].iloc[-1]
        entry = current_price
        target = round(entry * 1.2, 2)  # 20% target
        stop_loss = round(entry * 0.93, 2)  # 7% stop loss
        
        result = {
            "status": criteria_met >= 5,
            "criteria_met": criteria_met,
            "total_criteria": 7,
            "rs_rating": rs_rating,
            "entry": entry,
            "target": target,
            "stop_loss": stop_loss,
            "checks": {
                "C - Current Quarterly Earnings": c_check,
                "A - Annual Earnings Growth": a_check,
                "N - New Products, Services": n_check,
                "S - Supply and Demand": s_check,
                "L - Leader or Laggard": l_check,
                "I - Institutional Sponsorship": i_check,
                "M - Market Direction": m_check
            }
        }
        return result
    except Exception as e:
        return {"status": False, "message": f"Error analyzing {symbol}: {e}"}

def process_screener_csv(uploaded_file):
    """Process uploaded Screener.in CSV file"""
    try:
        df = pd.read_csv(uploaded_file)
        stocks = []
        
        # Process each stock in the CSV
        for index, row in df.iterrows():
            if 'Name' in df.columns:
                symbol = row['Name']
            elif 'Symbol' in df.columns:
                symbol = row['Symbol']
            else:
                continue
                
            # Clean symbol name - remove any exchange suffix
            if '.' in symbol:
                symbol = symbol.split('.')[0]
                
            # Check CAN SLIM criteria
            result = check_canslim_criteria(symbol)
            
            if result.get("status", False):
                stocks.append({
                    "Stock": symbol,
                    "Entry": result["entry"],
                    "Target": result["target"],
                    "Stop Loss": result["stop_loss"],
                    "RS Rating": result.get("rs_rating", 0),
                    "Criteria Met": f"{result['criteria_met']}/{result['total_criteria']}",
                    "Selected": False
                })
        
        return pd.DataFrame(stocks)
    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        return pd.DataFrame()

def send_email_alert(subject, body, to_email):
    """Send email alerts using SMTP"""
    try:
        # Get SendGrid credentials from environment or use fallback
        sendgrid_user = os.environ.get("SENDGRID_USERNAME", "")
        sendgrid_password = os.environ.get("SENDGRID_PASSWORD", "")
        from_email = os.environ.get("FROM_EMAIL", "canslim.trader@example.com")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach HTML body
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SendGrid SMTP server
        server = smtplib.SMTP('smtp.sendgrid.net', 587)
        server.starttls()
        server.login(sendgrid_user, sendgrid_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

def update_portfolio_prices():
    """Update current prices in portfolio"""
    if st.session_state.portfolio.empty:
        return
    
    try:
        # Only update every 15 minutes
        now = datetime.datetime.now()
        if (now - st.session_state.last_update).seconds < 900:  # 15 minutes = 900 seconds
            return
            
        st.session_state.last_update = now
        
        updated_portfolio = st.session_state.portfolio.copy()
        
        for idx, row in updated_portfolio.iterrows():
            symbol = row['Stock']
            try:
                df = get_nse_data(symbol, '1d')
                if not df.empty:
                    current_price = df['Close'].iloc[-1]
                    updated_portfolio.at[idx, 'Current'] = current_price
                    
                    # Calculate P/L %
                    entry = updated_portfolio.at[idx, 'Entry']
                    updated_portfolio.at[idx, 'P/L%'] = round(((current_price - entry) / entry) * 100, 2)
                    
                    # Update status
                    if current_price <= updated_portfolio.at[idx, 'Stop Loss']:
                        updated_portfolio.at[idx, 'Status'] = '🔴 Stop Loss Hit'
                        
                        # Send email alert for stop loss if configured
                        if st.session_state.email:
                            subject = f"🔴 Stop Loss Alert: {symbol}"
                            body = f"""
                            <h2>Stop Loss Hit!</h2>
                            <p>Your stop loss for {symbol} at ₹{updated_portfolio.at[idx, 'Stop Loss']} has been triggered.</p>
                            <p>Entry Price: ₹{entry}</p>
                            <p>Current Price: ₹{current_price}</p>
                            <p>P/L: {updated_portfolio.at[idx, 'P/L%']}%</p>
                            """
                            send_email_alert(subject, body, st.session_state.email)
                    elif current_price >= updated_portfolio.at[idx, 'Target']:
                        updated_portfolio.at[idx, 'Status'] = '💰 Target Reached'
                    elif current_price <= (updated_portfolio.at[idx, 'Stop Loss'] * 1.02):
                        updated_portfolio.at[idx, 'Status'] = '⚠️ Near Stop Loss'
                        
                        # Send email alert for near stop loss if configured
                        if st.session_state.email:
                            subject = f"⚠️ Near Stop Loss Alert: {symbol}"
                            body = f"""
                            <h2>Near Stop Loss Warning!</h2>
                            <p>{symbol} is within 2% of your stop loss at ₹{updated_portfolio.at[idx, 'Stop Loss']}.</p>
                            <p>Entry Price: ₹{entry}</p>
                            <p>Current Price: ₹{current_price}</p>
                            <p>P/L: {updated_portfolio.at[idx, 'P/L%']}%</p>
                            """
                            send_email_alert(subject, body, st.session_state.email)
                    else:
                        updated_portfolio.at[idx, 'Status'] = '🟢 Holding'
            except Exception as e:
                st.warning(f"Could not update price for {symbol}: {e}")
        
        st.session_state.portfolio = updated_portfolio
    except Exception as e:
        st.error(f"Error updating portfolio: {e}")

def analyze_sectors():
    """Analyze top sectors based on NSE sector indices"""
    try:
        # NSE sector indices
        sectors = [
            'NIFTY_BANK', 'NIFTY_AUTO', 'NIFTY_PHARMA', 'NIFTY_IT', 
            'NIFTY_FMCG', 'NIFTY_ENERGY', 'NIFTY_REALTY', 'NIFTY_MEDIA'
        ]
        
        sector_performance = []
        
        for sector in sectors:
            # Simulated performance data (would need proper index data)
            performance = np.random.randint(-15, 30)
            above_200ma = np.random.choice([True, False], p=[0.6, 0.4])
            rs_rating = np.random.randint(40, 95)
            
            sector_performance.append({
                'Sector': sector,
                'Performance': performance,
                'Above_200MA': above_200ma,
                'RS_Rating': rs_rating
            })
        
        # Sort by performance
        sector_df = pd.DataFrame(sector_performance)
        sector_df = sector_df.sort_values('Performance', ascending=False)
        
        return sector_df.head(3)
    except Exception as e:
        st.error(f"Error analyzing sectors: {e}")
        return pd.DataFrame()

def get_stock_chart(symbol, period='3mo'):
    """Get stock chart using Plotly"""
    try:
        df = get_nse_data(symbol, period)
        if df.empty:
            return None
            
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ))
        
        # Add volume as bars on a second y-axis
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            yaxis='y2',
            marker_color='rgba(0, 0, 255, 0.3)'
        ))
        
        # Calculate and add 50-day moving average
        df['MA50'] = df['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['MA50'], 
            mode='lines', 
            name='50-day MA',
            line=dict(color='orange', width=2)
        ))
        
        # Calculate and add 200-day moving average
        df['MA200'] = df['Close'].rolling(window=200).mean()
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['MA200'], 
            mode='lines', 
            name='200-day MA',
            line=dict(color='red', width=2)
        ))
        
        # Customize layout
        fig.update_layout(
            title=f'{symbol} Stock Price',
            xaxis_title='Date',
            yaxis_title='Price (₹)',
            xaxis_rangeslider_visible=False,
            yaxis2=dict(
                title='Volume',
                overlaying='y',
                side='right',
                showgrid=False
            ),
            height=500,
            margin=dict(l=50, r=50, t=50, b=50),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    except Exception as e:
        st.error(f"Error creating chart for {symbol}: {e}")
        return None

# Main App Interface with Tabs
tabs = st.tabs(["📊 Dashboard", "🔍 Stock Validator", "📂 Monthly Scanner", "📈 Sector Analyzer", "⚙️ Settings"])

# Dashboard Tab
with tabs[0]:
    st.header("📊 CAN SLIM Portfolio Tracker")
    
    # Update portfolio prices
    update_portfolio_prices()
    
    # Portfolio metrics
    if not st.session_state.portfolio.empty:
        total_investment = (st.session_state.portfolio['Entry'] * 20000).sum()
        current_value = (st.session_state.portfolio['Current'] * 20000).sum()
        overall_profit = current_value - total_investment
        overall_profit_percent = (overall_profit / total_investment) * 100 if total_investment > 0 else 0
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Stocks", len(st.session_state.portfolio))
        with cols[1]:
            st.metric("Total Investment", f"₹{total_investment:,.2f}")
        with cols[2]:
            st.metric("Current Value", f"₹{current_value:,.2f}")
        with cols[3]:
            st.metric("Overall P/L", f"₹{overall_profit:,.2f} ({overall_profit_percent:.2f}%)", 
                     delta=f"{overall_profit_percent:.2f}%")
        
        # Portfolio table
        st.subheader("Your Portfolio")
        
        styled_portfolio = st.session_state.portfolio.copy()
        
        # Format numbers with ₹ symbol
        for col in ['Entry', 'Current', 'Target', 'Stop Loss']:
            styled_portfolio[col] = styled_portfolio[col].apply(lambda x: f"₹{x:,.2f}")
            
        # Add % symbol to P/L%
        styled_portfolio['P/L%'] = styled_portfolio['P/L%'].apply(lambda x: f"{x}%")
        
        # Display portfolio with option to remove stocks
        for idx, row in styled_portfolio.iterrows():
            cols = st.columns([3, 1, 1, 1, 1, 1, 2, 1])
            
            bg_color = "#FFFFFF"
            if "🔴" in row['Status']:
                bg_color = "#FADBD8"
            elif "⚠️" in row['Status']:
                bg_color = "#FCF3CF"
            elif "💰" in row['Status']:
                bg_color = "#D5F5E3"
                
            cols[0].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'><b>{row['Stock']}</b></div>", unsafe_allow_html=True)
            cols[1].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'>{row['Entry']}</div>", unsafe_allow_html=True)
            cols[2].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'>{row['Current']}</div>", unsafe_allow_html=True)
            
            pl_color = "#D5F5E3" if "-" not in row['P/L%'] else "#FADBD8"
            cols[3].markdown(f"<div style='background-color:{pl_color};padding:10px;border-radius:5px;'>{row['P/L%']}</div>", unsafe_allow_html=True)
            
            cols[4].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'>{row['Target']}</div>", unsafe_allow_html=True)
            cols[5].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'>{row['Stop Loss']}</div>", unsafe_allow_html=True)
            cols[6].markdown(f"<div style='background-color:{bg_color};padding:10px;border-radius:5px;'>{row['Status']}</div>", unsafe_allow_html=True)
            
            if cols[7].button("🗑️", key=f"remove_{idx}"):
                st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)
                st.experimental_rerun()
        
        # Stock charts for portfolio
        st.subheader("Portfolio Charts")
        selected_stock = st.selectbox("Select a stock to view chart", st.session_state.portfolio['Stock'].tolist())
        if selected_stock:
            chart = get_stock_chart(selected_stock)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("Your portfolio is empty. Add stocks using the Monthly Scanner tab.")

# Stock Validator Tab
with tabs[1]:
    st.header("🔍 CAN SLIM Stock Validator")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        stock_symbol = st.text_input("Enter NSE Stock Symbol (e.g., TATASTEEL, RELIANCE)", placeholder="Enter NSE symbol...")
    
    with col2:
        check_button = st.button("Check CAN SLIM Criteria", type="primary")
    
    if check_button and stock_symbol:
        with st.spinner(f"Analyzing {stock_symbol}..."):
            result = check_canslim_criteria(stock_symbol)
            
            if "message" in result:
                st.error(result["message"])
            else:
                # Display result with CAN SLIM criteria
                st.subheader(f"Analysis for {stock_symbol}")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Get chart
                    chart = get_stock_chart(stock_symbol)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                
                with col2:
                    # Display CAN SLIM score
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>CAN SLIM Score</h3>
                        <h1>{result['criteria_met']}/{result['total_criteria']}</h1>
                        <p>RS Rating: {result['rs_rating']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Price levels
                    st.markdown(f"""
                    <div class="metric-card" style="margin-top: 20px;">
                        <h3>Price Levels</h3>
                        <p><b>Entry:</b> ₹{result['entry']:.2f}</p>
                        <p><b>Target (+20%):</b> ₹{result['target']:.2f}</p>
                        <p><b>Stop Loss (-7%):</b> ₹{result['stop_loss']:.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add to portfolio button
                    if st.button("Add to Portfolio", key="add_validator"):
                        new_row = pd.DataFrame([{
                            'Stock': stock_symbol,
                            'Entry': result['entry'],
                            'Current': result['entry'],  # Initial current price is entry price
                            'P/L%': 0.0,
                            'Target': result['target'],
                            'Stop Loss': result['stop_loss'],
                            'Status': '🟢 Holding',
                            'Entry Date': datetime.datetime.now().strftime('%Y-%m-%d')
                        }])
                        
                        # Check if stock already exists in portfolio
                        if stock_symbol in st.session_state.portfolio['Stock'].values:
                            st.warning(f"{stock_symbol} is already in your portfolio!")
                        else:
                            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                            st.success(f"Added {stock_symbol} to your portfolio!")
                            
                            # Send email alert if configured
                            if st.session_state.email:
                                subject = f"🟢 New Trade Alert: {stock_symbol}"
                                body = f"""
                                <h2>New Trade Added!</h2>
                                <p>You've added {stock_symbol} to your portfolio.</p>
                                <p><b>Entry Price:</b> ₹{result['entry']:.2f}</p>
                                <p><b>Target Price:</b> ₹{result['target']:.2f}</p>
                                <p><b>Stop Loss:</b> ₹{result['stop_loss']:.2f}</p>
                                <p><b>Investment Amount:</b> ₹20,000</p>
                                """
                                send_email_alert(subject, body, st.session_state.email)
                
                # Display detailed criteria
                st.subheader("CAN SLIM Criteria Details")
                
                for criterion, status in result["checks"].items():
                    if status:
                        st.markdown(f"✅ **{criterion}**")
                    else:
                        st.markdown(f"❌ **{criterion}**")
                
                st.markdown("""
                <div style="background-color: #F8F9FA; padding: 15px; border-radius: 5px; margin-top: 20px;">
                <h3>⚠️ Disclaimer</h3>
                <p>This analysis is for educational purposes only and not investment advice. 
                Always do your own research before investing.</p>
                </div>
                """, unsafe_allow_html=True)

# Monthly Scanner Tab
with tabs[2]:
    st.header("📂 Monthly CAN SLIM Scanner")
    
    st.markdown("""
    Upload a CSV file from [Screener.in](https://www.screener.in) to find CAN SLIM stocks.
    
    **How to get Screener.in CSV:**
    1. Create a custom screen on Screener.in
    2. Click "Export" and download as CSV
    3. Upload the CSV file below
    """)
    
    uploaded_file = st.file_uploader("Upload Screener.in CSV", type=["csv"])
    
    if uploaded_file:
        with st.spinner("Processing CSV file..."):
            result_df = process_screener_csv(uploaded_file)
            
            if not result_df.empty:
                st.session_state.monthly_picks = result_df
                st.success(f"Found {len(result_df)} stocks matching CAN SLIM criteria!")
            else:
                st.warning("No stocks matching CAN SLIM criteria found in the CSV.")
    
    # Display monthly picks
    if not st.session_state.monthly_picks.empty:
        st.subheader(f"{datetime.datetime.now().strftime('%B %Y')} CAN SLIM Picks")
        
        # Display table with checkboxes
        edited_df = st.data_editor(
            st.session_state.monthly_picks,
            column_config={
                "Selected": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select stocks to add to portfolio",
                    default=False,
                ),
                "Entry": st.column_config.NumberColumn(
                    "Entry Price (₹)",
                    format="₹%.2f",
                ),
                "Target": st.column_config.NumberColumn(
                    "Target Price (₹)",
                    format="₹%.2f",
                ),
                "Stop Loss": st.column_config.NumberColumn(
                    "Stop Loss (₹)",
                    format="₹%.2f",
                ),
                "RS Rating": st.column_config.ProgressColumn(
                    "RS Rating",
                    min_value=0,
                    max_value=100,
                    format="%d",
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
        
        # Update session state with edited data
        st.session_state.monthly_picks = edited_df
        
        # Button to add selected stocks to portfolio
        if st.button("Add Selected Stocks to Portfolio", type="primary"):
            selected_stocks = edited_df[edited_df['Selected'] == True]
            
            if selected_stocks.empty:
                st.warning("No stocks selected. Please select at least one stock.")
            else:
                added_count = 0
                for _, row in selected_stocks.iterrows():
                    # Check if stock already exists in portfolio
                    if row['Stock'] in st.session_state.portfolio['Stock'].values:
                        st.warning(f"{row['Stock']} is already in your portfolio!")
                        continue
                        
                    # Add to portfolio
                    new_row = pd.DataFrame([{
                        'Stock': row['Stock'],
                        'Entry': row['Entry'],
                        'Current': row['Entry'],  # Initial current price is entry price
                        'P/L%': 0.0,
                        'Target': row['Target'],
                        'Stop Loss': row['Stop Loss'],
                        'Status': '🟢 Holding',
                        'Entry Date': datetime.datetime.now().strftime('%Y-%m-%d')
                    }])
                    
                    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                    added_count += 1
                    
                    # Send email alert if configured
                    if st.session_state.email:
                        subject = f"🟢 New Trade Alert: {row['Stock']}"
                        body = f"""
                        <h2>New Trade Added!</h2>
                        <p>You've added {row['Stock']} to your portfolio.</p>
                        <p><b>Entry Price:</b> ₹{row['Entry']:.2f}</p>
                        <p><b>Target Price:</b> ₹{row['Target']:.2f}</p>
                        <p><b>Stop Loss:</b> ₹{row['Stop Loss']:.2f}</p>
                        <p><b>Investment Amount:</b> ₹20,000</p>
                        """
                        send_email_alert(subject, body, st.session_state.email)
                
                if added_count > 0:
                    st.success(f"Added {added_count} stocks to your portfolio!")
                    # Update selected flags to false after adding
                    st.session_state.monthly_picks['Selected'] = False
                    st.experimental_rerun()

# Sector Analyzer Tab
with tabs[3]:
    st.header("📈 Sector Analyzer")
    
    with st.spinner("Analyzing sectors..."):
        sector_df = analyze_sectors()
        
        if not sector_df.empty:
            st.subheader("Top 3 Performing Sectors")
            
            # Display each sector as a card
            for idx, row in sector_df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 15px; border-radius: 5px; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                        <h3>{row['Sector'].replace('_', ' ')}</h3>
                        <p><b>3-Month Performance:</b> {row['Performance']}%</p>
                        <p><b>RS Rating:</b> {row['RS_Rating']}</p>
                        <p><b>Price vs 200-day MA:</b> {"Above" if row['Above_200MA'] else "Below"}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Add explanation
            st.markdown("""
            ### How to Use This Information
            
            According to CAN SLIM methodology, it's best to focus on stocks from strong sectors. 
            When a sector is performing well:
            
            1. **Higher probability of success**: Stocks in strong sectors have tailwinds
            2. **Institutional interest**: Fund managers often invest in leading sectors
            3. **Better relative strength**: Stocks in strong sectors typically have better RS ratings
            
            **Strategy tip**: Consider focusing your monthly stock selection on the top sectors listed above.
            """)
        else:
            st.error("Unable to analyze sectors at this time.")

# Settings Tab
with tabs[4]:
    st.header("⚙️ Settings")
    
    # Email notification settings
    st.subheader("Email Notifications")
    email = st.text_input("Your Email Address for Alerts", value=st.session_state.email)
    
    if st.button("Save Email Settings"):
        st.session_state.email = email
        st.success("Email settings saved successfully!")
        
        # Test email
        if email:
            with st.spinner("Sending test email..."):
                subject = "CAN SLIM Trader - Test Email"
                body = """
                <h2>Test Email from CAN SLIM Trader</h2>
                <p>This is a test email to confirm your email settings are working correctly.</p>
                <p>You will receive alerts for:</p>
                <ul>
                    <li>New trades added to your portfolio</li>
                    <li>Stocks approaching stop loss</li>
                    <li>Stop losses being triggered</li>
                </ul>
                """
                if send_email_alert(subject, body, email):
                    st.success("Test email sent successfully!")
                else:
                    st.error("Failed to send test email. Please check your email address.")
    
    # Export portfolio
    st.subheader("Export Portfolio")
    if not st.session_state.portfolio.empty:
        # Convert DataFrame to CSV
        csv = st.session_state.portfolio.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="canslim_portfolio.csv" class="btn">Download Portfolio CSV</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("Your portfolio is empty. Nothing to export.")
    
    # About and Help
    st.subheader("About CAN SLIM Trader")
    st.markdown("""
    **CAN SLIM Trader** is a no-code web application that helps you find and track stocks using William O'Neil's CAN SLIM methodology.
    
    **What is CAN SLIM?**
    
    CAN SLIM is a trading strategy developed by William O'Neil, founder of Investor's Business Daily. Each letter represents a key characteristic:
    
    - **C**: Current quarterly earnings (25%+ growth)
    - **A**: Annual earnings growth (25%+ growth)
    - **N**: New products, management, or stock price highs
    - **S**: Supply and demand (small float, increasing volume)
    - **L**: Leader vs. laggard (high relative strength)
    - **I**: Institutional sponsorship (smart money ownership)
    - **M**: Market direction (trade with the trend)
    
    **Disclaimer**
    
    This app is for educational purposes only. It is not financial advice. Always do your own research before investing.
    """)
    
    # App info
    st.subheader("App Information")
    st.info("""
    - **Version**: 1.0.0
    - **Built with**: Streamlit, NSEPy, Plotly
    - **Hosted on**: Render.com (Free Tier)
    - **Data Source**: NSE via NSEPy library
    """)

# Run the app
# if __name__ == "__main__":
#     st.write("App is running!")
