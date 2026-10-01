import os
import logging
import yfinance as yf
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Quotex Major & Popular Pairs
PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/CAD": "AUDCAD=X"
}

def analyze_quotex_1min(symbol: str):
    try:
        # Fetching 1-minute candle data
        data = yf.download(tickers=symbol, period="1d", interval="1m")
        if data.empty or len(data) < 30:
            return "⚠️ Market data process nahi ho saka. Baraye meharbani dobara try karein."
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        # Support and Resistance Calculation (Last 30 Candles)
        support = low.tail(30).min().item()
        resistance = high.tail(30).max().item()
        current_price = close.iloc[-1].item()
        
        # RSI 14 Calculation
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1].item()
        
        # EMA 20 Calculation
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1].item()
        
        # Professional Strategy Logic (S&R + RSI + EMA)
        signal = "🟡 NEUTRAL / WAIT"
        direction = "WAIT ⏳"
        reason = "Market range mein hai. Agli candle ka wait karein."
        
        # Buy Signal Conditions (Bounce from Support / RSI Oversold / Above EMA)
        if (current_price <= support * 1.0002 or rsi < 35) and current_price > ema20:
            signal = "🟢 CALL / BUY (GREEN CANDLE 🟢)"
            direction = "UP ⬆️️"
            reason = "Price Strong Support ke pas hai + RSI Oversold hai. Green Candle ki trade lein."
            
        # Sell Signal Conditions (Rejection from Resistance / RSI Overbought / Below EMA)
        elif (current_price >= resistance * 0.9998 or rsi > 65) and current_price < ema20:
            signal = "🔴 PUT / SELL (RED CANDLE 🔴)"
            direction = "DOWN ⬇️"
            reason = "Price Strong Resistance ke pas hai + RSI Overbought hai. Red Candle ki trade lein."

        text = (
            f"📊 **QUOTEX 1-MIN SIGNAL** ({symbol})\n"
            f"-----------------------------------\n"
            f"💵 **Current Price:** `{current_price:.5f}`\n"
            f"🛡️ **Support:** `{support:.5f}`\n"
            f"🧱 **Resistance:** `{resistance:.5f}`\n"
            f"📈 **RSI (14):** `{rsi:.2f}`\n"
            f"📊 **EMA (20):** `{ema20:.5f}`\n\n"
            f"🎯 **Trade Direction:** {direction}\n"
            f"🚦 **Signal:** {signal}\n\n"
            f"💡 **Analysis:** {reason}\n"
            f"⏱ **Expiry Time:** 1 Minute"
        )
        return text
    except Exception as e:
        return f"❌ Analysis mein error aaya: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎯 GET 1-MIN SIGNAL", callback_data="get_signal")],
        [InlineKeyboardButton("📊 SELECT QUOTEX PAIR", callback_data="select_pair")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📈 **Quotex Professional 1-Min Trading Engine**\n\nApna Pair select karein aur 1-Minute Candle ka Professional Signal hasil karein:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_pair = context.user_data.get("pair", "EURUSD=X")
    
    if query.data == "get_signal":
        await query.edit_message_text("🔍 Support & Resistance + RSI Analyze ho raha hai... 1-2 sec wait karein.")
        result = analyze_quotex_1min(selected_pair)
        
        keyboard = [
            [InlineKeyboardButton("🔄 REFRESH SIGNAL", callback_data="get_signal")],
            [InlineKeyboardButton("📊 SELECT PAIR", callback_data="select_pair")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=result, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "select_pair":
        keyboard = []
        for name, sym in PAIRS.items():
            keyboard.append([InlineKeyboardButton(f"📊 {name}", callback_data=f"setpair_{sym}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Quotex ka Pair muntakhib (Select) karein:", reply_markup=reply_markup)
        
    elif query.data.startswith("setpair_"):
        pair_sym = query.data.split("setpair_")[1]
        context.user_data["pair"] = pair_sym
        
        keyboard = [
            [InlineKeyboardButton("🎯 GET 1-MIN SIGNAL", callback_data="get_signal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"✅ Quotex Pair Set Ho Gaya: `{pair_sym}`\nAb Signal button dabayein.", parse_mode="Markdown", reply_markup=reply_markup)

def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN missing!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Quotex Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
