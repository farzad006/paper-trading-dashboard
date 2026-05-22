import sqlite3
import json
import csv
from datetime import datetime
from collections import defaultdict
import os

CSV_PATH = "paper_trades_report.csv"
IGNORED_CSV_PATH = "ignored_trades_report.csv"

def get_trades_data():
    trades = []
    ignored = []
    
    # Read executed trades from CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append((
                    row['entry_time'],
                    row['exit_time'],
                    row['side'],
                    float(row['entry_price']),
                    float(row['exit_price']),
                    float(row['pnl_rupees']),
                    row['exit_reason'],
                    row['instrument']
                ))
    
    # Read ignored trades from CSV
    if os.path.exists(IGNORED_CSV_PATH):
        with open(IGNORED_CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ignored.append((
                    row['timestamp'],
                    row['reason']
                ))
    
    return trades, ignored

def analyze_trades(trades, ignored):
    if not trades:
        return None
    
    # Calculate metrics
    total_trades = len(trades)
    wins = [t for t in trades if t[5] > 0]
    losses = [t for t in trades if t[5] <= 0]
    
    total_pnl = sum(t[5] for t in trades)
    total_points = total_pnl / 75  # Convert to points (lot size 75)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = sum(t[5] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t[5] for t in losses) / len(losses) if losses else 0
    
    gross_profit = sum(t[5] for t in wins)
    gross_loss = abs(sum(t[5] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Daily breakdown
    daily_stats = defaultdict(lambda: {'trades': [], 'ignored': 0})
    
    for trade in trades:
        date = trade[0][:10]
        daily_stats[date]['trades'].append(trade)
    
    for ig in ignored:
        date = ig[0][:10]
        daily_stats[date]['ignored'] += 1
    
    # Month breakdown
    month_stats = defaultdict(lambda: {'trades': [], 'ignored': 0})
    
    for trade in trades:
        month = trade[0][:7]  # YYYY-MM
        month_stats[month]['trades'].append(trade)
    
    for ig in ignored:
        month = ig[0][:7]
        month_stats[month]['ignored'] += 1
    
    # Trade direction (signal is BUY or SELL)
    buy_trades = [t for t in trades if t[2] == 'BUY']
    sell_trades = [t for t in trades if t[2] == 'SELL']
    
    # Exit reasons
    exit_reasons = defaultdict(int)
    for trade in trades:
        exit_reasons[trade[6]] += 1
    
    return {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'total_points': total_points,
        'win_rate': win_rate,
        'wins': len(wins),
        'losses': len(losses),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'ignored_count': len(ignored),
        'daily_stats': dict(daily_stats),
        'month_stats': dict(month_stats),
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'exit_reasons': dict(exit_reasons),
        'best_trade': max(trades, key=lambda x: x[5]) if trades else None,
        'worst_trade': min(trades, key=lambda x: x[5]) if trades else None,
    }

def generate_html(data):
    if not data:
        return "<html><body><h1>No trades found</h1></body></html>"
    
    # Generate month options
    months = sorted(data['month_stats'].keys(), reverse=True)
    month_options = ''.join([f'<option value="{m}">{datetime.strptime(m, "%Y-%m").strftime("%B %Y")}</option>' for m in months])
    
    # Convert data to JSON for JavaScript
    trades_json = json.dumps({
        'daily': {date: {
            'trades': len(stats['trades']),
            'wins': len([t for t in stats['trades'] if t[5] > 0]),
            'losses': len([t for t in stats['trades'] if t[5] <= 0]),
            'pnl': sum(t[5] for t in stats['trades']),
            'points': sum(t[5] for t in stats['trades']) / 75,
            'ignored': stats['ignored']
        } for date, stats in data['daily_stats'].items()},
        'monthly': {month: {
            'trades': len(stats['trades']),
            'wins': len([t for t in stats['trades'] if t[5] > 0]),
            'losses': len([t for t in stats['trades'] if t[5] <= 0]),
            'pnl': sum(t[5] for t in stats['trades']),
            'points': sum(t[5] for t in stats['trades']) / 75,
            'ignored': stats['ignored'],
            'win_rate': (len([t for t in stats['trades'] if t[5] > 0]) / len(stats['trades']) * 100) if stats['trades'] else 0
        } for month, stats in data['month_stats'].items()}
    })
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <title>Paper Trading Dashboard - Live</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; margin-bottom: 10px; font-size: 32px; }}
        .subtitle {{ color: #7f8c8d; margin-bottom: 20px; font-size: 16px; }}
        
        .controls {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; display: flex; gap: 20px; align-items: center; }}
        .controls select {{ padding: 10px 15px; border: 2px solid #3498db; border-radius: 6px; font-size: 14px; cursor: pointer; }}
        .controls button {{ padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .controls button:hover {{ background: #2980b9; }}
        .auto-refresh {{ color: #27ae60; font-size: 13px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stat-card h3 {{ color: #7f8c8d; font-size: 14px; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 36px; font-weight: bold; margin-bottom: 5px; }}
        .stat-card .subtext {{ color: #95a5a6; font-size: 13px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #3498db; }}
        
        .section {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; font-size: 24px; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #34495e; color: white; padding: 12px; text-align: left; font-weight: 600; font-size: 13px; }}
        td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; font-size: 14px; }}
        tr:hover {{ background: #f8f9fa; }}
        
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 8px; }}
        .badge-success {{ background: #27ae60; color: white; }}
        .badge-danger {{ background: #e74c3c; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Paper Trading Dashboard</h1>
        <p class="subtitle">Live Performance Analysis | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="controls">
            <label><strong>View:</strong></label>
            <select id="viewMode" onchange="changeView()">
                <option value="all">All Time</option>
                <option value="month">Month Wise</option>
            </select>
            <select id="monthSelect" style="display:none;" onchange="filterByMonth()">
                <option value="">Select Month</option>
                {month_options}
            </select>
            <button onclick="location.reload()">🔄 Refresh Now</button>
            <span class="auto-refresh">⏱️ Auto-refresh every 5 minutes</span>
        </div>
        
        <div id="statsContainer">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Trades</h3>
                    <div class="value neutral" id="totalTrades">{data['total_trades']}</div>
                    <div class="subtext">Executed trades</div>
                </div>
                <div class="stat-card">
                    <h3>Net P&L</h3>
                    <div class="value {'positive' if data['total_pnl'] > 0 else 'negative'}" id="netPnl">₹{data['total_pnl']:,.2f}</div>
                    <div class="subtext" id="netPoints">{data['total_points']:+.1f} points</div>
                </div>
                <div class="stat-card">
                    <h3>Win Rate</h3>
                    <div class="value neutral" id="winRate">{data['win_rate']:.2f}%</div>
                    <div class="subtext" id="winLoss">{data['wins']} wins / {data['losses']} losses</div>
                </div>
                <div class="stat-card">
                    <h3>Avg Win</h3>
                    <div class="value positive" id="avgWin">₹{data['avg_win']:,.2f}</div>
                    <div class="subtext">Per winning trade</div>
                </div>
                <div class="stat-card">
                    <h3>Avg Loss</h3>
                    <div class="value negative" id="avgLoss">₹{data['avg_loss']:,.2f}</div>
                    <div class="subtext">Per losing trade</div>
                </div>
                <div class="stat-card">
                    <h3>Profit Factor</h3>
                    <div class="value positive" id="profitFactor">{data['profit_factor']:.2f}</div>
                    <div class="subtext">Gross profit / Gross loss</div>
                </div>
                <div class="stat-card">
                    <h3>Ignored Trades</h3>
                    <div class="value neutral" id="ignoredTrades">{data['ignored_count']}</div>
                    <div class="subtext">Due to daily limits</div>
                </div>
                <div class="stat-card">
                    <h3>Best Trade</h3>
                    <div class="value positive" id="bestTrade">₹{data['best_trade'][5]:,.2f}</div>
                    <div class="subtext">{data['best_trade'][0][:10]}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 id="tableTitle">📅 Daily Performance Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Trades</th>
                        <th>Wins</th>
                        <th>Losses</th>
                        <th>Win Rate</th>
                        <th>Daily P&L</th>
                        <th>Points</th>
                        <th>Ignored</th>
                    </tr>
                </thead>
                <tbody id="performanceTable">
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        const tradesData = {trades_json};
        let currentView = 'all';
        let selectedMonth = '';
        
        function changeView() {{
            currentView = document.getElementById('viewMode').value;
            const monthSelect = document.getElementById('monthSelect');
            
            if (currentView === 'month') {{
                monthSelect.style.display = 'inline-block';
                if (monthSelect.value) {{
                    filterByMonth();
                }} else {{
                    showMonthlyView();
                }}
            }} else {{
                monthSelect.style.display = 'none';
                showAllTimeView();
            }}
        }}
        
        function showAllTimeView() {{
            document.getElementById('tableTitle').textContent = '📅 Daily Performance Breakdown';
            const tbody = document.getElementById('performanceTable');
            tbody.innerHTML = '';
            
            const sortedDates = Object.keys(tradesData.daily).sort();
            sortedDates.forEach(date => {{
                const day = tradesData.daily[date];
                const winRate = day.trades > 0 ? (day.wins / day.trades * 100).toFixed(1) : '0.0';
                const row = `
                    <tr>
                        <td>${{date}}</td>
                        <td>${{day.trades}}</td>
                        <td>${{day.wins}}</td>
                        <td>${{day.losses}}</td>
                        <td>${{winRate}}%</td>
                        <td class="${{day.pnl > 0 ? 'positive' : 'negative'}}">₹${{day.pnl.toFixed(2)}}</td>
                        <td>${{day.points > 0 ? '+' : ''}}${{day.points.toFixed(1)}}</td>
                        <td>${{day.ignored}}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            }});
        }}
        
        function showMonthlyView() {{
            document.getElementById('tableTitle').textContent = '📅 Monthly Performance Summary';
            const tbody = document.getElementById('performanceTable');
            tbody.innerHTML = '';
            
            const sortedMonths = Object.keys(tradesData.monthly).sort().reverse();
            sortedMonths.forEach(month => {{
                const data = tradesData.monthly[month];
                const monthName = new Date(month + '-01').toLocaleDateString('en-US', {{ year: 'numeric', month: 'long' }});
                const row = `
                    <tr style="cursor:pointer;" onclick="selectMonth('${{month}}')">
                        <td><strong>${{monthName}}</strong></td>
                        <td>${{data.trades}}</td>
                        <td>${{data.wins}}</td>
                        <td>${{data.losses}}</td>
                        <td>${{data.win_rate.toFixed(1)}}%</td>
                        <td class="${{data.pnl > 0 ? 'positive' : 'negative'}}">₹${{data.pnl.toFixed(2)}}</td>
                        <td>${{data.points > 0 ? '+' : ''}}${{data.points.toFixed(1)}}</td>
                        <td>${{data.ignored}}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            }});
        }}
        
        function selectMonth(month) {{
            document.getElementById('monthSelect').value = month;
            filterByMonth();
        }}
        
        function filterByMonth() {{
            selectedMonth = document.getElementById('monthSelect').value;
            if (!selectedMonth) {{
                showMonthlyView();
                return;
            }}
            
            const monthData = tradesData.monthly[selectedMonth];
            const monthName = new Date(selectedMonth + '-01').toLocaleDateString('en-US', {{ year: 'numeric', month: 'long' }});
            
            // Update stats
            document.getElementById('totalTrades').textContent = monthData.trades;
            document.getElementById('netPnl').textContent = '₹' + monthData.pnl.toFixed(2);
            document.getElementById('netPnl').className = 'value ' + (monthData.pnl > 0 ? 'positive' : 'negative');
            document.getElementById('netPoints').textContent = (monthData.points > 0 ? '+' : '') + monthData.points.toFixed(1) + ' points';
            document.getElementById('winRate').textContent = monthData.win_rate.toFixed(2) + '%';
            document.getElementById('winLoss').textContent = monthData.wins + ' wins / ' + monthData.losses + ' losses';
            document.getElementById('ignoredTrades').textContent = monthData.ignored;
            
            // Show daily breakdown for selected month
            document.getElementById('tableTitle').textContent = `📅 Daily Breakdown - ${{monthName}}`;
            const tbody = document.getElementById('performanceTable');
            tbody.innerHTML = '';
            
            const daysInMonth = Object.keys(tradesData.daily).filter(date => date.startsWith(selectedMonth)).sort();
            daysInMonth.forEach(date => {{
                const day = tradesData.daily[date];
                const winRate = day.trades > 0 ? (day.wins / day.trades * 100).toFixed(1) : '0.0';
                const row = `
                    <tr>
                        <td>${{date}}</td>
                        <td>${{day.trades}}</td>
                        <td>${{day.wins}}</td>
                        <td>${{day.losses}}</td>
                        <td>${{winRate}}%</td>
                        <td class="${{day.pnl > 0 ? 'positive' : 'negative'}}">₹${{day.pnl.toFixed(2)}}</td>
                        <td>${{day.points > 0 ? '+' : ''}}${{day.points.toFixed(1)}}</td>
                        <td>${{day.ignored}}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            }});
        }}
        
        // Initialize
        showAllTimeView();
    </script>
</body>
</html>"""
    
    return html

def main():
    print("Generating dashboard from database...")
    trades, ignored = get_trades_data()
    data = analyze_trades(trades, ignored)
    
    if data:
        html = generate_html(data)
        with open('dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Dashboard generated successfully!")
        print(f"Total Trades: {data['total_trades']}")
        print(f"Net P&L: Rs.{data['total_pnl']:,.2f}")
        print(f"Win Rate: {data['win_rate']:.2f}%")
    else:
        print("No trades found in database")

if __name__ == "__main__":
    main()
