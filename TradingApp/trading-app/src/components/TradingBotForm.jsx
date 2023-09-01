import React, { useState } from 'react';
import axios from 'axios';
import './TradingBotForm.css';
import { TextField, Button, Container, Typography, createTheme, ThemeProvider, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Link } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const theme = createTheme({
    typography: {
        color: '#e0e0e0',
    },
});

function TradingBotForm() {
    const [userId, setUserId] = useState('');
    const [password, setPassword] = useState('');
    const [xtbPair, setXtbPair] = useState('');
    const [yahooPair, setYahooPair] = useState('');
    const [chartInterval, setChartInterval] = useState('');

    const [dialogOpen, setDialogOpen] = useState(false);

    const startBot = async (e) => {
        e.preventDefault();
    
        const data = {
            user_id: userId,
            password: password,
            xtb_pair: xtbPair,
            yahoo_pair: yahooPair,
            chart_interval: chartInterval
        };
    
        try {
            const response = await axios.post('http://localhost:5000/start_bot', data);
            console.log(response.data);
            setDialogOpen(true);  // Open the dialog
        } catch (error) {
            console.error("Error starting bot:", error);
        }
    };    

    return (
        <ThemeProvider theme={theme}>
            <div className="landing-container">
                <Container component="main" maxWidth="xs">
                    <Typography style={{ fontFamily: 'Poppins' }} variant="h5" align="center" sx={{ color: '#2e3951', margin: '20px 0', fontSize: '2.5rem', fontWeight: 600 }}>
                        New Trading Bot
                    </Typography>

                    <form onSubmit={startBot}>
                        <TextField 
                            variant="outlined"
                            margin="normal"
                            required
                            fullWidth
                            id="userId"
                            label="User ID"
                            value={userId}
                            onChange={e => setUserId(e.target.value)}
                        />
                        <TextField 
                            variant="outlined"
                            margin="normal"
                            required
                            fullWidth
                            name="password"
                            label="Password"
                            type="password"
                            id="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />

                        <FormControl fullWidth variant="outlined" margin="normal">
                            <InputLabel htmlFor="xtbPair">XTB Pair</InputLabel>
                            <Select
                                value={xtbPair}
                                onChange={e => setXtbPair(e.target.value)}
                                label="XTB Pair"
                                id="xtbPair"
                            >
                                <MenuItem value="EURUSD">EURUSD</MenuItem>
                                <MenuItem value="EURGBP">EURGBP</MenuItem>
                                {/* Add other pairs as needed */}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth variant="outlined" margin="normal">
                            <InputLabel htmlFor="yahooPair">Yahoo Pair</InputLabel>
                            <Select
                                value={yahooPair}
                                onChange={e => setYahooPair(e.target.value)}
                                label="Yahoo Pair"
                                id="yahooPair"
                            >
                                <MenuItem value="EURUSD=X">EURUSD=X</MenuItem>
                                <MenuItem value="EURGBP=X">EURGBP=X</MenuItem>
                                {/* Add other pairs as needed */}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth variant="outlined" margin="normal">
                            <InputLabel htmlFor="chartInterval">Chart Interval</InputLabel>
                            <Select
                                value={chartInterval}
                                onChange={e => setChartInterval(e.target.value)}
                                label="Chart Interval"
                                id="chartInterval"
                            >
                                <MenuItem value="30m">30m</MenuItem>
                                <MenuItem value="1h">1h</MenuItem>
                                <MenuItem value="1d">1d</MenuItem>
                                {/* Add other intervals as needed */}
                            </Select>
                        </FormControl>

                        <Button 
                            type="submit"
                            fullWidth
                            variant="contained"
                            color="primary"
                            style={{ marginTop: '10px' }}
                        >
                            Start Bot
                        </Button>
                    </form>
                </Container>
            </div>

            <Dialog
                open={dialogOpen}
                onClose={() => setDialogOpen(false)}
                aria-labelledby="alert-dialog-title"
                aria-describedby="alert-dialog-description"
                sx={{ 
                    "& .MuiDialog-paper": { 
                        width: '80%', 
                        maxWidth: '400px', 
                        paddingBottom: '20px', 
                        paddingTop: '20px', 
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',  // semi-transparent background
                        opacity: 0.7,  // Slightly reduced overall transparency
                        borderRadius: '20px'  // More rounded corners
                    } 
                }}
            >
                <DialogContent style={{ textAlign: 'center', paddingTop: '20px', paddingBottom: '20px' }}>
                    <CheckCircleIcon style={{ color: 'green', fontSize: '3rem', marginBottom: '10px' }} />
                    <DialogTitle id="alert-dialog-title" align="center" sx={{ color: '#d1d1d1' }}>Bot was created Successfully</DialogTitle>  {/* Lighter color for header text */}
                    <DialogContentText id="alert-dialog-description" sx={{ color: '#9fa8a3', textAlign: 'center' }}>
                        Go to running Bots overview or run another bot.
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ justifyContent: 'center' }}>
                    <Link href="/new" style={{ marginRight: '20px' }} underline="none">Create another</Link>
                    <Link href="/" underline="none">Overview</Link>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}

export default TradingBotForm;
