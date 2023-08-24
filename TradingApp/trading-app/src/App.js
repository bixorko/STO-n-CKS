import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Drawer, IconButton, List, ListItem, ListItemIcon, ListItemText, AppBar, Toolbar, CssBaseline } from '@mui/material';
import { Menu, Dashboard, Build } from '@mui/icons-material';
import TradingBotForm from './components/TradingBotForm';
import Overview from './components/Overview';
import './App.css';

function App() {
    const [open, setOpen] = useState(false);

    return (
        <Router>
            <div className="App">
                <CssBaseline />
                <AppBar 
                    position="fixed" 
                    style={{ 
                        background: 'linear-gradient(135deg, #3a475d, #24313f)', 
                        boxShadow: '0px 0px 10px 2px rgba(0, 0, 0, 0.2)' 
                    }}
                >
                    <Toolbar>
                        <IconButton edge="start" color="inherit" onClick={() => setOpen(true)}>
                            <Menu />
                        </IconButton>
                        <h2 style={{ flexGrow: 1, color: '#e0e0e0' }}>XTB Trading Bot</h2>
                    </Toolbar>
                </AppBar>


                <Toolbar /> 

                <Drawer
                    variant="persistent"
                    anchor="left"
                    open={open}
                    sx={{ 
                        '.MuiDrawer-paper': { 
                            background: '#2e3951',
                            color: '#e0e0e0',
                            width: 250 
                        }
                    }}
                >
                    <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'space-between', 
                        padding: '8px', 
                        background: 'linear-gradient(135deg, #3a475d, #24313f)' 
                    }}>
                        <h2 style={{ flexGrow: 1, color: '#e0e0e0' }}>Menu</h2>
                        <IconButton onClick={() => setOpen(!open)} style={{ color: '#e0e0e0' }}>
                            <Menu />
                        </IconButton>
                    </div>
                    <List>
                        <ListItem 
                            button 
                            onClick={() => window.location.href='/new'}
                            sx={{
                                '&:hover': { background: '#3a475d' }
                            }}
                        >
                            <ListItemIcon sx={{ color: '#a5b3c2' }}><Build /></ListItemIcon>
                            <ListItemText primary="New Trading Bot" />
                        </ListItem>
                        <ListItem 
                            button 
                            onClick={() => window.location.href='/'}
                            sx={{
                                '&:hover': { background: '#3a475d' }
                            }}
                        >
                            <ListItemIcon sx={{ color: '#a5b3c2' }}><Dashboard /></ListItemIcon>
                            <ListItemText primary="Overview" />
                        </ListItem>
                    </List>
                </Drawer>

                <div className="main-content" style={{ paddingLeft: open ? '250px' : '0', paddingRight: '20px' }}>
                    <Routes>
                        <Route path="/new" element={<TradingBotForm />} />
                        <Route path="/" element={<Overview />} />
                    </Routes>
                </div>

            </div>
        </Router>
    );
}

export default App;
