import React, { useState, useEffect } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CardActionArea from '@mui/material/CardActionArea';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Link from '@mui/material/Link';
import './Overview.css';

function Overview() {
    const [botsInfo, setBotsInfo] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedBotId, setSelectedBotId] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    
    useEffect(() => {
        // Fetch bot info when component mounts
        fetch('http://localhost:5000/get_all_bot_info')
            .then(response => response.json())
            .then(data => {
                setBotsInfo(data);
                setIsLoading(false); // Set isLoading to false after fetching
            })
            .catch(err => {
                console.error("Failed to fetch bot info:", err);
                setIsLoading(false); // Set isLoading to false even if there's an error
            });
    }, []);


    const handleOpenDialog = (botId) => {
        setSelectedBotId(botId);
        setDialogOpen(true);
    };

    const handleCloseDialog = () => {
        setSelectedBotId(null);
        setDialogOpen(false);
    };

    const handleDeleteBot = () => {
        fetch(`http://localhost:5000/delete_bot/${selectedBotId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    alert(data.message);
                    // Directly update state without refetching the data
                    const updatedBots = botsInfo.filter(bot => bot.bot_id !== selectedBotId);
                    setBotsInfo(updatedBots);
                } else {
                    alert(data.error);
                }
            });
        handleCloseDialog();
    };
    
    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <CircularProgress />
            </div>
        );
    }

    if (botsInfo.length === 0) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                No Running Bots
            </div>
        );
    }

    return (
        <div className="card-container">
            {botsInfo.map((botInfo, index) => (
                <Card key={index} className="card-overview">
                    <button onClick={() => handleOpenDialog(botInfo.bot_id)} style={{position: 'absolute', top: '5px', right: '5px'}}>X</button>
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
                            <Typography 
                                className={
                                    `flex-center ${botInfo.trend === 'Bullish' ? "highlight" : 
                                    botInfo.trend === 'Bearish' ? "lowlight" : ""}`
                                }
                            >
                                {botInfo.trend === 'Bullish' && <ArrowUpwardIcon color="inherit" style={{ marginRight: '10px' }} />}
                                {botInfo.trend === 'Bearish' && <ArrowDownwardIcon color="inherit" style={{ marginRight: '10px' }} />}
                                {botInfo.trend}
                            </Typography>

                        </CardContent>
                    </CardActionArea>
                </Card>
            ))}
            <Dialog
                open={dialogOpen}
                onClose={handleCloseDialog}
                aria-labelledby="alert-dialog-title"
                aria-describedby="alert-dialog-description"
                sx={{ 
                    "& .MuiDialog-paper": { 
                        width: '80%', 
                        maxWidth: '400px', 
                        paddingBottom: '20px', 
                        paddingTop: '20px', 
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',  
                        opacity: 0.7,  
                        borderRadius: '20px'  
                    } 
                }}
            >
                <DialogContent style={{ textAlign: 'center', paddingTop: '20px', paddingBottom: '20px' }}>
                    <DialogTitle id="alert-dialog-title" align="center" sx={{ color: '#d1d1d1' }}>Confirm Deletion</DialogTitle>
                    <DialogContentText id="alert-dialog-description" sx={{ color: '#9fa8a3', textAlign: 'center' }}>
                        Are you sure you want to delete this bot?
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ justifyContent: 'center' }}>
                    <Link component="button" onClick={handleCloseDialog} style={{ marginRight: '20px' }} underline="none">Cancel</Link>
                    <Link component="button" onClick={handleDeleteBot} underline="none">Delete</Link>
                </DialogActions>
            </Dialog>
        </div>
    );    
}

export default Overview;
