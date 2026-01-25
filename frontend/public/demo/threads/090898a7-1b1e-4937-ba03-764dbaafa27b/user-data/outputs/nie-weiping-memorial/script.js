// 聂卫平纪念网站 - 交互效果

document.addEventListener('DOMContentLoaded', function() {
    // 初始化
    initNavigation();
    initScrollEffects();
    initStatsCounter();
    initGoBoard();
    initBackToTop();
    initAnimations();
    initCandleMemorial(); // 初始化蜡烛纪念功能
    
    console.log('棋圣聂卫平纪念网站已加载 - 永恒的围棋传奇');
});

// 导航菜单功能
function initNavigation() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');
    
    // 切换移动端菜单
    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });
    
    // 点击导航链接时关闭菜单
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });
    
    // 滚动时高亮当前部分
    window.addEventListener('scroll', highlightCurrentSection);
}

// 高亮当前滚动到的部分
function highlightCurrentSection() {
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('.nav-link');
    
    let currentSection = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        const sectionHeight = section.clientHeight;
        const scrollPosition = window.scrollY;
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            currentSection = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${currentSection}`) {
            link.classList.add('active');
        }
    });
}

// 滚动效果
function initScrollEffects() {
    // 添加滚动时的淡入效果
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
            }
        });
    }, observerOptions);
    
    // 观察需要动画的元素
    const animatedElements = document.querySelectorAll('.timeline-item, .achievement-card, .game-quote, .legacy-text, .legacy-image');
    animatedElements.forEach(el => observer.observe(el));
    
    // 平滑滚动到锚点
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// 统计数据计数器
function initStatsCounter() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    const observerOptions = {
        threshold: 0.5
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const statNumber = entry.target;
                const target = parseInt(statNumber.getAttribute('data-count'));
                const duration = 2000; // 2秒
                const increment = target / (duration / 16); // 60fps
                let current = 0;
                
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= target) {
                        current = target;
                        clearInterval(timer);
                    }
                    statNumber.textContent = Math.floor(current);
                }, 16);
                
                observer.unobserve(statNumber);
            }
        });
    }, observerOptions);
    
    statNumbers.forEach(number => observer.observe(number));
}

// 围棋棋盘初始化
function initGoBoard() {
    const boardStones = document.querySelector('.board-stones');
    if (!boardStones) return;
    
    // 经典棋局棋子位置 (模拟1985年决胜局)
    const stonePositions = [
        { type: 'black', x: 4, y: 4 },
        { type: 'white', x: 4, y: 16 },
        { type: 'black', x: 16, y: 4 },
        { type: 'white', x: 16, y: 16 },
        { type: 'black', x: 10, y: 10 },
        { type: 'white', x: 9, y: 9 },
        { type: 'black', x: 3, y: 15 },
        { type: 'white', x: 15, y: 3 },
        { type: 'black', x: 17, y: 17 },
        { type: 'white', x: 2, y: 2 }
    ];
    
    // 创建棋子
    stonePositions.forEach((stone, index) => {
        const stoneElement = document.createElement('div');
        stoneElement.className = `board-stone ${stone.type}`;
        
        // 计算位置 (19x19棋盘)
        const xPercent = (stone.x / 18) * 100;
        const yPercent = (stone.y / 18) * 100;
        
        stoneElement.style.left = `${xPercent}%`;
        stoneElement.style.top = `${yPercent}%`;
        stoneElement.style.animationDelay = `${index * 0.2}s`;
        
        boardStones.appendChild(stoneElement);
    });
    
    // 添加棋盘样式
    const style = document.createElement('style');
    style.textContent = `
        .board-stone {
            position: absolute;
            width: 4%;
            height: 4%;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            animation: stoneAppear 0.5s ease-out forwards;
            opacity: 0;
        }
        
        .board-stone.black {
            background: radial-gradient(circle at 30% 30%, #555, #000);
        }
        
        .board-stone.white {
            background: radial-gradient(circle at 30% 30%, #fff, #ddd);
            border: 1px solid #aaa;
        }
        
        @keyframes stoneAppear {
            from {
                opacity: 0;
                transform: translate(-50%, -50%) scale(0);
            }
            to {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
        }
    `;
    
    document.head.appendChild(style);
}

// 返回顶部按钮
function initBackToTop() {
    const backToTopBtn = document.querySelector('.back-to-top');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 300) {
            backToTopBtn.classList.add('visible');
        } else {
            backToTopBtn.classList.remove('visible');
        }
    });
    
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// 初始化动画
function initAnimations() {
    // 添加滚动时的水墨效果
    let lastScrollTop = 0;
    const inkSplatter = document.querySelector('.ink-splatter');
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.scrollY;
        const scrollDirection = scrollTop > lastScrollTop ? 'down' : 'up';
        
        // 根据滚动方向调整水墨效果
        if (inkSplatter) {
            const opacity = 0.1 + (scrollTop / 5000);
            inkSplatter.style.opacity = Math.min(opacity, 0.3);
            
            // 轻微移动效果
            const moveX = (scrollTop % 100) / 100;
            inkSplatter.style.transform = `translateX(${moveX}px)`;
        }
        
        lastScrollTop = scrollTop;
    });
    
    // 鼠标移动时的墨水效果
    document.addEventListener('mousemove', function(e) {
        const floatingStones = document.querySelectorAll('.floating-stone');
        
        floatingStones.forEach((stone, index) => {
            const speed = 0.01 + (index * 0.005);
            const x = (window.innerWidth - e.clientX) * speed;
            const y = (window.innerHeight - e.clientY) * speed;
            
            stone.style.transform = `translate(${x}px, ${y}px)`;
        });
    });
    
    // 页面加载时的动画序列
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
}

// 添加键盘快捷键
document.addEventListener('keydown', function(e) {
    // 空格键滚动
    if (e.code === 'Space' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        window.scrollBy({
            top: window.innerHeight * 0.8,
            behavior: 'smooth'
        });
    }
    
    // ESC键返回顶部
    if (e.code === 'Escape') {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
    
    // 数字键跳转到对应部分
    if (e.code >= 'Digit1' && e.code <= 'Digit5') {
        const sectionIndex = parseInt(e.code.replace('Digit', '')) - 1;
        const sections = ['home', 'life', 'achievements', 'gallery', 'legacy'];
        
        if (sectionIndex < sections.length) {
            const targetSection = document.getElementById(sections[sectionIndex]);
            if (targetSection) {
                window.scrollTo({
                    top: targetSection.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        }
    }
});

// 添加打印友好功能
window.addEventListener('beforeprint', function() {
    document.body.classList.add('printing');
});

window.addEventListener('afterprint', function() {
    document.body.classList.remove('printing');
});

// 性能优化：图片懒加载
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                }
                imageObserver.unobserve(img);
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => imageObserver.observe(img));
}

// 添加触摸设备优化
if ('ontouchstart' in window) {
    document.body.classList.add('touch-device');
    
    // 为触摸设备调整悬停效果
    const style = document.createElement('style');
    style.textContent = `
        .touch-device .achievement-card:hover {
            transform: none;
        }
        
        .touch-device .btn:hover {
            transform: none;
        }
    `;
    document.head.appendChild(style);
}

// 添加页面可见性API支持
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('页面隐藏中...');
    } else {
        console.log('页面恢复显示');
    }
});

// 错误处理
window.addEventListener('error', function(e) {
    console.error('页面错误:', e.message);
});

// 蜡烛纪念功能
function initCandleMemorial() {
    const candleGrid = document.querySelector('.candle-grid');
    const lightCandleBtn = document.querySelector('.light-candle-btn');
    const resetCandlesBtn = document.querySelector('.reset-candles-btn');
    const autoLightBtn = document.querySelector('.auto-light-btn');
    const countNumber = document.querySelector('.count-number');
    const messageText = document.querySelector('.message-text');
    
    if (!candleGrid) return;
    
    // 蜡烛数量
    const candleCount = 24; // 24支蜡烛，象征24小时永恒纪念
    let litCandles = 0;
    let candles = [];
    
    // 初始化蜡烛
    function createCandles() {
        candleGrid.innerHTML = '';
        candles = [];
        litCandles = 0;
        
        for (let i = 0; i < candleCount; i++) {
            const candle = document.createElement('div');
            candle.className = 'candle-item';
            candle.dataset.index = i;
            
            candle.innerHTML = `
                <div class="candle-flame">
                    <div class="flame-core"></div>
                    <div class="flame-outer"></div>
                    <div class="flame-spark"></div>
                    <div class="flame-spark"></div>
                    <div class="flame-spark"></div>
                </div>
                <div class="candle-body"></div>
            `;
            
            // 点击点亮/熄灭蜡烛
            candle.addEventListener('click', function() {
                toggleCandle(i);
            });
            
            candleGrid.appendChild(candle);
            candles.push({
                element: candle,
                lit: false
            });
        }
        
        updateCounter();
    }
    
    // 切换蜡烛状态
    function toggleCandle(index) {
        const candle = candles[index];
        
        if (candle.lit) {
            // 熄灭蜡烛
            candle.element.classList.remove('candle-lit');
            candle.lit = false;
            litCandles--;
            
            // 添加熄灭动画
            candle.element.style.animation = 'none';
            setTimeout(() => {
                candle.element.style.animation = '';
            }, 10);
        } else {
            // 点亮蜡烛
            candle.element.classList.add('candle-lit');
            candle.lit = true;
            litCandles++;
            
            // 添加点亮动画
            candle.element.style.animation = 'candleLightUp 0.5s ease';
        }
        
        updateCounter();
        updateMessage();
        saveCandleState();
    }
    
    // 点亮一支蜡烛
    function lightOneCandle() {
        // 找到未点亮的蜡烛
        const unlitCandles = candles.filter(c => !c.lit);
        if (unlitCandles.length === 0) return false;
        
        // 随机选择一支
        const randomIndex = Math.floor(Math.random() * unlitCandles.length);
        const candleIndex = candles.indexOf(unlitCandles[randomIndex]);
        
        toggleCandle(candleIndex);
        return true;
    }
    
    // 自动点亮所有蜡烛
    function autoLightCandles() {
        if (litCandles === candleCount) return;
        
        let delay = 0;
        for (let i = 0; i < candles.length; i++) {
            if (!candles[i].lit) {
                setTimeout(() => {
                    toggleCandle(i);
                }, delay);
                delay += 100; // 每100毫秒点亮一支
            }
        }
    }
    
    // 重置所有蜡烛
    function resetAllCandles() {
        candles.forEach((candle, index) => {
            if (candle.lit) {
                candle.element.classList.remove('candle-lit');
                candle.lit = false;
                
                // 添加重置动画
                candle.element.style.animation = 'none';
                setTimeout(() => {
                    candle.element.style.animation = '';
                }, 10);
            }
        });
        
        litCandles = 0;
        updateCounter();
        updateMessage();
        saveCandleState();
    }
    
    // 更新计数器
    function updateCounter() {
        if (countNumber) {
            countNumber.textContent = litCandles;
            
            // 添加计数动画
            countNumber.style.transform = 'scale(1.2)';
            setTimeout(() => {
                countNumber.style.transform = 'scale(1)';
            }, 200);
        }
    }
    
    // 更新消息
    function updateMessage() {
        if (!messageText) return;
        
        const messages = [
            "您的缅怀将永远铭记",
            "一烛一缅怀，光明永相传",
            "棋圣精神，永垂不朽",
            "黑白之间，永恒追忆",
            "围棋之光，永不熄灭",
            "传承是最好的纪念"
        ];
        
        // 根据点亮数量选择消息
        let messageIndex;
        if (litCandles === 0) {
            messageIndex = 0;
        } else if (litCandles < candleCount / 2) {
            messageIndex = 1;
        } else if (litCandles < candleCount) {
            messageIndex = 2;
        } else {
            messageIndex = 3;
        }
        
        // 随机选择同级别的消息
        const startIndex = Math.floor(messageIndex / 2) * 2;
        const endIndex = startIndex + 2;
        const availableMessages = messages.slice(startIndex, endIndex);
        const randomMessage = availableMessages[Math.floor(Math.random() * availableMessages.length)];
        
        messageText.textContent = randomMessage;
    }
    
    // 保存蜡烛状态到本地存储
    function saveCandleState() {
        try {
            const candleState = candles.map(c => c.lit);
            localStorage.setItem('nieCandleState', JSON.stringify(candleState));
            localStorage.setItem('nieCandleCount', litCandles.toString());
        } catch (e) {
            console.log('无法保存蜡烛状态:', e);
        }
    }
    
    // 加载蜡烛状态
    function loadCandleState() {
        try {
            const savedState = localStorage.getItem('nieCandleState');
            const savedCount = localStorage.getItem('nieCandleCount');
            
            if (savedState) {
                const candleState = JSON.parse(savedState);
                candleState.forEach((isLit, index) => {
                    if (isLit && candles[index]) {
                        candles[index].element.classList.add('candle-lit');
                        candles[index].lit = true;
                    }
                });
                
                litCandles = savedCount ? parseInt(savedCount) : candleState.filter(Boolean).length;
                updateCounter();
                updateMessage();
            }
        } catch (e) {
            console.log('无法加载蜡烛状态:', e);
        }
    }
    
    // 初始化
    createCandles();
    
    // 加载保存的状态
    setTimeout(() => {
        loadCandleState();
    }, 100);
    
    // 按钮事件
    if (lightCandleBtn) {
        lightCandleBtn.addEventListener('click', function() {
            if (!lightOneCandle()) {
                // 所有蜡烛都已点亮
                this.innerHTML = '<i class="fas fa-check"></i> 所有蜡烛已点亮';
                this.disabled = true;
                setTimeout(() => {
                    this.innerHTML = '<i class="fas fa-fire"></i> 点亮蜡烛';
                    this.disabled = false;
                }, 2000);
            }
        });
    }
    
    if (resetCandlesBtn) {
        resetCandlesBtn.addEventListener('click', function() {
            if (confirm('确定要熄灭所有蜡烛吗？')) {
                resetAllCandles();
            }
        });
    }
    
    if (autoLightBtn) {
        autoLightBtn.addEventListener('click', function() {
            autoLightCandles();
        });
    }
    
    // 添加键盘快捷键
    document.addEventListener('keydown', function(e) {
        // C键点亮一支蜡烛
        if (e.code === 'KeyC' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            lightOneCandle();
        }
        
        // R键重置蜡烛
        if (e.code === 'KeyR' && e.ctrlKey && !e.target.matches('input, textarea')) {
            e.preventDefault();
            resetAllCandles();
        }
        
        // A键自动点亮
        if (e.code === 'KeyA' && e.ctrlKey && !e.target.matches('input, textarea')) {
            e.preventDefault();
            autoLightCandles();
        }
    });
    
    console.log('蜡烛纪念功能已初始化');
}

// 页面卸载前的确认
window.addEventListener('beforeunload', function(e) {
    // 可以在这里添加保存功能
});