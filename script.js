// Animation des compteurs de statistiques
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        const speed = target > 1000 ? 200 : 50;
        
        let count = 0;
        const updateCount = () => {
            const increment = target / speed;
            
            if (count < target) {
                count += increment;
                if (count > target) count = target;
                
                // Formatage des nombres
                if (target >= 1000000) {
                    counter.textContent = (count / 1000000).toFixed(1) + 'M';
                } else if (target >= 1000) {
                    counter.textContent = (count / 1000).toFixed(0) + 'K';
                } else {
                    counter.textContent = Math.ceil(count) + (target === 99 ? '.9' : '');
                }
                
                requestAnimationFrame(updateCount);
            }
        };
        
        updateCount();
    });
}

// Observer pour déclencher les animations au scroll
const observerCallback = (entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            if (entry.target.classList.contains('stats')) {
                animateCounters();
            }
            
            // Animation pour les cartes de fonctionnalités
            if (entry.target.classList.contains('feature-card')) {
                entry.target.style.animationDelay = `${Math.random() * 0.5}s`;
                entry.target.classList.add('animate-on-scroll');
            }
        }
    });
};

const observer = new IntersectionObserver(observerCallback, {
    threshold: 0.1
});

// Observer les sections
document.addEventListener('DOMContentLoaded', () => {
    const statsSection = document.querySelector('.stats');
    const featureCards = document.querySelectorAll('.feature-card');
    
    if (statsSection) observer.observe(statsSection);
    featureCards.forEach(card => observer.observe(card));
});

// Gestion de la navigation mobile
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.querySelector('.nav-menu');

if (navToggle) {
    navToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });
}

// Scroll fluide pour les liens de navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Effet parallax pour le hero
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero');
    const particles = document.querySelector('.particles');
    const cyberGrid = document.querySelector('.cyber-grid');
    
    if (hero && scrolled < hero.offsetHeight) {
        const rate = scrolled * -0.5;
        if (particles) particles.style.transform = `translateY(${rate}px)`;
        if (cyberGrid) cyberGrid.style.transform = `translateY(${rate * 0.3}px)`;
    }
});

// Animation des modèles 3D au survol
document.addEventListener('DOMContentLoaded', () => {
    const models = document.querySelectorAll('.floating-model');
    
    models.forEach(model => {
        model.addEventListener('mouseenter', () => {
            model.style.filter = 'drop-shadow(0 0 40px var(--neon-green)) brightness(1.2)';
            model.style.transform = 'scale(1.1)';
        });
        
        model.addEventListener('mouseleave', () => {
            model.style.filter = 'drop-shadow(0 0 20px var(--neon-blue))';
            model.style.transform = 'scale(1)';
        });
    });
});

// Génération de particules additionnelles
function createParticles() {
    const particleContainer = document.querySelector('.particles');
    if (!particleContainer) return;
    
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: 2px;
            height: 2px;
            background: var(--neon-blue);
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation: particleFloat ${5 + Math.random() * 10}s linear infinite;
            animation-delay: ${Math.random() * 5}s;
            opacity: ${0.3 + Math.random() * 0.7};
        `;
        particleContainer.appendChild(particle);
    }
}

// Fonction de connexion Steam
async function connectSteam() {
    try {
        // Créer un popup de chargement
        showLoadingPopup();
        
        // Générer un token unique pour la session
        const token = generateSessionToken();
        
        // Récupérer l'ID Discord de l'utilisateur (à adapter selon votre système)
        const discordId = getDiscordId();
        
        if (!discordId) {
            alert('Vous devez d\'abord vous connecter à Discord pour lier votre compte Steam.');
            hideLoadingPopup();
            return;
        }
        
        // URL Steam OpenID avec redirection vers notre API
        const steamUrl = `https://steamcommunity.com/openid/login?` +
            `openid.ns=http://specs.openid.net/auth/2.0&` +
            `openid.mode=checkid_setup&` +
            `openid.return_to=${encodeURIComponent(window.location.origin + '/api/steam-callback?discord_id=' + discordId + '&token=' + token)}&` +
            `openid.realm=${encodeURIComponent(window.location.origin)}&` +
            `openid.identity=http://specs.openid.net/auth/2.0/identifier_select&` +
            `openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select`;
        
        // Ouvrir la fenêtre Steam
        const steamWindow = window.open(steamUrl, 'steamLogin', 'width=800,height=600');
        
        // Surveiller la fermeture de la fenêtre
        const checkClosed = setInterval(() => {
            if (steamWindow.closed) {
                clearInterval(checkClosed);
                hideLoadingPopup();
                // Optionnel : recharger la page ou mettre à jour l'interface
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        }, 1000);
        
    } catch (error) {
        console.error('Erreur lors de la connexion Steam:', error);
        hideLoadingPopup();
        alert('Erreur lors de la connexion Steam. Veuillez réessayer.');
    }
}

// Fonctions utilitaires
function generateSessionToken() {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
}

function getDiscordId() {
    // À adapter selon votre système d'authentification Discord
    // Ceci est un exemple - vous devrez implémenter votre propre logique
    return localStorage.getItem('discord_user_id') || 
           sessionStorage.getItem('discord_user_id') ||
           '123456789012345678'; // ID de test
}

function showLoadingPopup() {
    const popup = document.createElement('div');
    popup.id = 'loading-popup';
    popup.innerHTML = `
        <div class="popup-backdrop">
            <div class="popup-content">
                <div class="loading-spinner"></div>
                <h3>Connexion à Steam</h3>
                <p>Redirection vers Steam en cours...</p>
            </div>
        </div>
    `;
    
    popup.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 10000;
    `;
    
    document.body.appendChild(popup);
    
    // Ajouter les styles CSS pour le popup
    const style = document.createElement('style');
    style.textContent = `
        .popup-backdrop {
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(5px);
        }
        
        .popup-content {
            background: var(--bg-dark);
            border: 2px solid var(--neon-blue);
            border-radius: 10px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 0 40px rgba(0, 212, 255, 0.3);
        }
        
        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(0, 212, 255, 0.3);
            border-top: 3px solid var(--neon-blue);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

function hideLoadingPopup() {
    const popup = document.getElementById('loading-popup');
    if (popup) {
        popup.remove();
    }
}

// Effets sonores (optionnel)
function playHoverSound() {
    // Créer un son synthétique pour les interactions
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);
}

// Ajouter les effets sonores aux boutons
document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.btn, .nav-link');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            try {
                playHoverSound();
            } catch (e) {
                // Ignorer les erreurs audio
            }
        });
    });
});

// Chargement dynamique des modèles 3D depuis models.json
async function loadModelsConfig() {
    try {
        const response = await fetch('/models.json');
        const config = await response.json();
        return config;
    } catch (error) {
        console.log('Configuration des modèles non trouvée, utilisation des modèles par défaut');
        return null;
    }
}

// Mise à jour des modèles avec la configuration
async function updateModelsWithConfig() {
    const config = await loadModelsConfig();
    if (!config) return;
    
    const models = document.querySelectorAll('.floating-model');
    models.forEach((model, index) => {
        const modelKeys = Object.keys(config.cs2_models.weapons);
        const equipmentKeys = Object.keys(config.cs2_models.equipment);
        const allKeys = [...modelKeys, ...equipmentKeys];
        
        if (allKeys[index]) {
            const categoryKey = modelKeys.includes(allKeys[index]) ? 'weapons' : 'equipment';
            const modelConfig = config.cs2_models[categoryKey][allKeys[index]];
            
            // Mise à jour des attributs avec fallback
            if (modelConfig.url) {
                model.src = modelConfig.url;
                model.addEventListener('error', () => {
                    model.src = modelConfig.fallback;
                });
            }
            
            if (modelConfig.description) {
                model.alt = modelConfig.description;
            }
        }
    });
}

// Effets de performance avancés
function optimizePerformance() {
    // Réduire les animations si l'utilisateur préfère moins de mouvement
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.querySelectorAll('.floating-model').forEach(model => {
            model.style.animation = 'none';
        });
        return;
    }
    
    // Ajuster la qualité selon les performances
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        
        // Réduire la qualité sur les GPU faibles
        if (renderer && renderer.includes('Intel')) {
            document.querySelectorAll('.floating-model').forEach(model => {
                model.style.width = '100px';
                model.style.height = '100px';
            });
        }
    }
}

// Analytics et tracking des interactions
function trackInteractions() {
    // Track clics sur les boutons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            console.log(`🎯 Interaction: ${e.target.textContent.trim()}`);
            
            // Ajouter effet de ripple
            const ripple = document.createElement('div');
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                width: 20px;
                height: 20px;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            const rect = e.target.getBoundingClientRect();
            ripple.style.left = (e.clientX - rect.left - 10) + 'px';
            ripple.style.top = (e.clientY - rect.top - 10) + 'px';
            
            e.target.style.position = 'relative';
            e.target.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    // Track survol des modèles 3D
    document.querySelectorAll('.floating-model').forEach(model => {
        model.addEventListener('model-viewer-loaded', () => {
            console.log(`🎮 Modèle 3D chargé: ${model.alt}`);
        });
    });
}

// Initialisation avancée
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Initialisation QuickFrag Ultra...');
    
    // Optimisations de performance
    optimizePerformance();
    
    // Chargement des modèles 3D
    await updateModelsWithConfig();
    
    // Création des particules
    setTimeout(createParticles, 1000);
    
    // Tracking des interactions
    trackInteractions();
    
    // Animation d'entrée pour les éléments
    const elementsToAnimate = document.querySelectorAll('.feature-card, .stat-item');
    elementsToAnimate.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(50px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.6s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Ajouter les styles pour l'effet ripple
    const rippleStyle = document.createElement('style');
    rippleStyle.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(rippleStyle);
    
    console.log('🎯 QuickFrag Site Ultra Moderne Initialisé!');
    console.log('⚡ Modèles 3D CS2 chargés avec succès');
    console.log('🎮 Interface futuriste prête');
});

// Easter egg : Konami Code
let konamiCode = [];
const konami = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];

document.addEventListener('keydown', (e) => {
    konamiCode.push(e.keyCode);
    if (konamiCode.length > konami.length) {
        konamiCode.shift();
    }
    
    if (konamiCode.join(',') === konami.join(',')) {
        // Activer le mode ultra futuriste
        document.body.style.filter = 'hue-rotate(180deg) saturate(2)';
        alert('🎮 MODE ULTRA FUTURISTE ACTIVÉ!');
        
        setTimeout(() => {
            document.body.style.filter = '';
        }, 5000);
    }
}); 