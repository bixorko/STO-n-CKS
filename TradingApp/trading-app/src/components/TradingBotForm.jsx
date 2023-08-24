import React, { useState } from 'react';
import axios from 'axios';
import './TradingBotForm.css';
import { TextField, Button, Container, Typography, createTheme, ThemeProvider, Select, MenuItem, FormControl, InputLabel } from '@mui/material';

const theme = createTheme({
    typography: {
        fontFamily: 'Roboto',
        color: '#e0e0e0',
    },
});

function TradingBotForm() {
    const [userId, setUserId] = useState('');
    const [password, setPassword] = useState('');
    const [xtbPair, setXtbPair] = useState('');
    const [yahooPair, setYahooPair] = useState('');
    const [chartInterval, setChartInterval] = useState('');

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
        } catch (error) {
            console.error("Error starting bot:", error);
        }
    };

    return (
        <ThemeProvider theme={theme}>
            <div className="landing-container">
                <Container component="main" maxWidth="xs">
                    <Typography variant="h5" align="center" sx={{ color: '#a5b3c2', margin: '20px 0', fontSize: '2.5rem', fontWeight: 600 }}>
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
        </ThemeProvider>
    );
}

export default TradingBotForm;
