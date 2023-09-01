import React, { useState, useEffect } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CardActionArea from '@mui/material/CardActionArea';
import CircularProgress from '@mui/material/CircularProgress';
import './Overview.css';

function Overview() {
    const [botsInfo, setBotsInfo] = useState([]);

    useEffect(() => {
        // Fetch bot info when component mounts
        fetch('http://localhost:5000/get_all_bot_info')
            .then(response => response.json())
            .then(data => setBotsInfo(data));
    }, []);

    if (botsInfo.length === 0) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><CircularProgress /></div>;

    return (
        <div className="card-container">
            {botsInfo.map((botInfo, index) => (
                <Card key={index} className="card-overview">
                    <CardActionArea>
                        <CardContent>
                            <Typography variant="h5">User ID: {botInfo.user_id}</Typography>
                            <Typography>Xtb Pair: {botInfo.xtb_pair}</Typography>
                            <Typography>Yahoo Pair: {botInfo.yahoo_pair}</Typography>
                            <Typography>Chart Interval: {botInfo.chart_interval}</Typography>
                            <Typography>EMA 5: {Number(botInfo.ema_5).toFixed(4)}</Typography>
                            <Typography>
                                EMA {isNaN(botInfo.ema_10) ? '15' : '10'}: {isNaN(botInfo.ema_10) ? Number(botInfo.ema_15).toFixed(4) : Number(botInfo.ema_10).toFixed(4)}
                            </Typography>
                            <Typography>MACD: {Number(botInfo.macd).toFixed(4)}</Typography>
                            <Typography>RSI: {Number(botInfo.rsi).toFixed(4)}</Typography>
                            <Typography>Spread: {botInfo.spread}</Typography>
                            <Typography className={
                                botInfo.trend === 'Bullish' ? "highlight" : 
                                botInfo.trend === 'Bearish' ? "lowlight" : ""
                            }>
                                Trend: 
                                {botInfo.trend === 'Bullish' && <ArrowUpwardIcon color="inherit" />}
                                {botInfo.trend === 'Bearish' && <ArrowDownwardIcon color="inherit" />}
                                {botInfo.trend}
                            </Typography>
                        </CardContent>
                    </CardActionArea>
                </Card>
            ))}
        </div>
    );    
}

export default Overview;