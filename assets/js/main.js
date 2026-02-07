// =============================================
// VOTING SYSTEM (No persistence - allows switching)
// =============================================

// Handle card click for voting
function handleCardVote(card, categoryId, cardId) {
    const categoryWrapper = card.closest('.pool-wrapper-t');
    const button = card.querySelector('.pool-card-btn');

    // Check if this card is already voted
    if (button.classList.contains('voted')) {
        return; // Already voted on this one
    }

    // Remove vote from previously selected card in this category
    const previouslyVoted = categoryWrapper.querySelector('.pool-card-btn.voted');
    if (previouslyVoted) {
        previouslyVoted.classList.remove('voted');
        previouslyVoted.textContent = 'Vote Now';
        const prevCard = previouslyVoted.closest('.pool-card');
        prevCard.classList.remove('voted-card');
    }

    // Add voting animation to card
    card.classList.add('voting');

    // After short delay, update button and add effect
    setTimeout(() => {
        button.classList.add('voted');
        button.textContent = 'Voted';

        // Add subtle shadow after shine completes
        setTimeout(() => {
            card.classList.remove('voting');
            card.classList.add('voted-card');

            // Improved navigation: Scroll to the *next unvoted* category
            const allCategories = Array.from(document.querySelectorAll('.pool-wrapper-t'));
            const currentIndex = allCategories.indexOf(categoryWrapper);

            let nextTarget = null;

            // Search forward from current position
            for (let i = currentIndex + 1; i < allCategories.length; i++) {
                if (!allCategories[i].querySelector('.voted-card')) {
                    nextTarget = allCategories[i];
                    break;
                }
            }

            if (nextTarget) {
                // Scroll to the next unvoted category
                lenis.scrollTo(nextTarget, {
                    offset: 0,
                    duration: 1.2,
                    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
                });
            } else {
                // If no more categories are missing *after this one*, 
                // check if there are any *before* (edge case) or just go to form.
                // The user logic implies forward flow, so we go to form.
                const formSection = document.getElementById('contact-form-section');
                if (formSection) {
                    lenis.scrollTo(formSection, {
                        offset: 0,
                        duration: 1.2,
                        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
                    });
                }
            }
        }, 300);
    }, 400);
}

// =============================================
// CONTACT FORM HANDLING
// =============================================

function createConfetti(button) {
    const container = document.createElement('div');
    container.className = 'confetti-container';

    // Create 8 confetti pieces
    for (let i = 0; i < 8; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        container.appendChild(confetti);
    }

    button.style.position = 'relative';
    button.appendChild(container);

    // Remove confetti after animation
    setTimeout(() => {
        container.remove();
    }, 1000);
}

function showPopup(isSuccess = true, title = 'Congratulations!', message = 'Your submission has been received successfully.') {
    const popup = document.getElementById('success-popup');
    if (popup) {
        // Toggle Icons
        const successIcon = document.getElementById('popup-success-icon');
        const errorIcon = document.getElementById('popup-error-icon');

        if (isSuccess) {
            successIcon?.classList.remove('hidden');
            errorIcon?.classList.add('hidden');
        } else {
            successIcon?.classList.add('hidden');
            errorIcon?.classList.remove('hidden');
        }

        // Set Text
        const titleEl = document.getElementById('popup-title');
        const msgEl = document.getElementById('popup-message');
        if (titleEl) titleEl.textContent = title;
        if (msgEl) msgEl.textContent = message;

        popup.classList.add('active');
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
}

function closePopup() {
    const popup = document.getElementById('success-popup');
    if (popup) {
        popup.classList.remove('active');
        // Restore body scroll
        document.body.style.overflow = '';
    }
}

function initContactForm() {
    const form = document.getElementById('contact-form');
    const section = document.getElementById('contact-form-section');
    const submitBtn = form?.querySelector('.form-submit-btn');

    if (!form || !section || !submitBtn) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Validation: Check if all categories have a vote
        const allCategories = document.querySelectorAll('.pool-wrapper-t');
        let firstUnvoted = null;
        const votes = [];

        for (const category of allCategories) {
            const votedCard = category.querySelector('.voted-card');
            if (!votedCard) {
                firstUnvoted = category;
                break;
            } else {
                votes.push({
                    category_id: parseInt(category.dataset.categoryId),
                    card_id: parseInt(votedCard.dataset.cardId)
                });
            }
        }

        if (firstUnvoted) {
            // Scroll to the first missing category
            lenis.scrollTo(firstUnvoted, {
                offset: 0,
                duration: 1.2,
                easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
            });

            // Blink the title
            const title = firstUnvoted.querySelector('.pool-title');
            if (title) {
                title.classList.add('blink-orange');
                setTimeout(() => {
                    title.classList.remove('blink-orange');
                }, 2000);
            }

            return; // Stop submission
        }

        // Add submitting animation to button
        submitBtn.classList.add('submitting');
        submitBtn.textContent = 'Submitting...';

        // Gather User Data
        const name = document.getElementById('name').value.trim();
        const phone = document.getElementById('phone').value.trim();
        const email = document.getElementById('email').value.trim();

        // Client-Side Validation
        if (!/^\d{10,15}$/.test(phone)) {
            showPopup(false, 'Invalid Phone Number', 'Please enter a valid phone number (10-15 digits only).');
            return;
        }

        // Basic Email Regex (Constraints also handled by input type="email")
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showPopup(false, 'Invalid Email', 'Please enter a valid email address.');
            return;
        }

        try {
            const response = await fetch('/api/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user: { name, phone, email },
                    votes: votes
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                const msg = errData.detail || errData.message || 'Submission failed. Please try again.';
                throw new Error(msg);
            }

            // Success Animation
            setTimeout(() => {
                submitBtn.classList.remove('submitting');
                submitBtn.classList.add('success');
                submitBtn.textContent = 'Submitted!';

                // Create confetti effect
                createConfetti(submitBtn);

                // Add success class to section (triggers trophy spin)
                section.classList.add('success');

                // Show popup after a delay
                setTimeout(() => {
                    showPopup(true);
                }, 800);

                // Reset form after animations complete
                setTimeout(() => {
                    form.reset();

                    // Reset Voting UI
                    document.querySelectorAll('.pool-card.voted-card').forEach(c => c.classList.remove('voted-card'));
                    document.querySelectorAll('.pool-card-btn.voted').forEach(btn => {
                        btn.classList.remove('voted');
                        btn.textContent = 'Vote Now';
                    });

                    // Scroll to Top
                    lenis.scrollTo(0, { duration: 1.5 });

                    // Reset button after delay
                    setTimeout(() => {
                        submitBtn.classList.remove('success');
                        submitBtn.textContent = 'Submit';
                        section.classList.remove('success');
                    }, 2000);
                }, 1000);
            }, 500);

        } catch (error) {
            console.error(error);
            submitBtn.classList.remove('submitting');
            submitBtn.textContent = 'Failed';

            // Show Error Popup
            showPopup(false, 'Submission Failed', error.message);

            setTimeout(() => {
                submitBtn.textContent = 'Submit';
            }, 3000);
        }
    });
}

// =============================================
// DYNAMIC CATEGORY RENDERING
// =============================================

// Render a single category
function renderCategory(category, index) {
    const cardsHTML = category.cards.map((card, cardIndex) => {
        return `
            <div class="pool-card" 
                 data-aos="fade-up" 
                 data-aos-duration="800" 
                 data-aos-delay="${cardIndex * 100}"
                 data-card-id="${card.id}"
                 onclick="handleCardVote(this, '${category.id}', '${card.id}')"
                 style="cursor: pointer;">
                <img src="${card.image_url}" alt="${card.title}">
                <div class="pool-card-text">
                    <h4 class="pool-card-title">
                        ${card.title}
                        ${card.subtitle ? `<span>${card.subtitle.split('//').join('<br>')}</span>` : ''}
                    </h4>
                    <button class="pool-card-btn">
                        Vote Now
                    </button>
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="pool-wrapper-t" data-category-id="${category.id}">
            <div class="container">
                <div class="pool-wrapper">
                    <div class="pool-header">
                        <div class="pool-divider mobile"></div>
                        <h3 class="pool-title">${category.title}</h3>
                        <div class="pool-divider"></div>
                    </div>
                    <div class="pool-card-wrapper">
                        ${cardsHTML}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Fetch and render all categories
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();

        // Backend returns { categories: [...] } where cards is a list inside category
        // We need to map backend structure to what renderCategory expects if different
        // Backend: { id, name, title, cards: [{ id, title, subtitle, image_url }] }
        // Frontend render expected: category.cards (mapped from cards)

        const categories = data.categories.map(cat => ({
            id: cat.id,
            title: cat.title || cat.name, // Use title if available
            name: cat.name,
            cards: cat.cards.map(card => ({
                id: card.id,
                title: card.title,
                subtitle: card.subtitle,
                image_url: card.image_url
            }))
        }));

        const container = document.getElementById('categories-container');
        container.innerHTML = categories.map((cat, idx) => renderCategory(cat, idx)).join('');

        // Initialize animations after content is loaded
        initializeAnimations();

    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// =============================================
// ANIMATIONS
// =============================================

function initializeAnimations() {
    // Initialize AOS with premium settings
    AOS.init({
        duration: 800,
        easing: 'ease-out-cubic',
        once: true,
        offset: 50
    });

    // Custom Intersection Observer for header animations (title + growing lines)
    const headerObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const header = entry.target;
                const title = header.querySelector('.pool-title');
                const dividers = header.querySelectorAll('.pool-divider');

                // Animate title letters one by one
                if (title && !title.classList.contains('split')) {
                    const text = title.textContent.trim();
                    title.innerHTML = '';
                    title.classList.add('split');

                    // Use Intl.Segmenter to properly split Malayalam grapheme clusters
                    let segments = [];
                    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
                        const segmenter = new Intl.Segmenter('ml', { granularity: 'grapheme' });
                        segments = [...segmenter.segment(text)].map(s => s.segment);
                    } else {
                        segments = text.split('');
                    }

                    // Create spans for each grapheme cluster
                    segments.forEach((char, index) => {
                        const span = document.createElement('span');
                        span.className = 'letter';
                        span.textContent = char === ' ' ? '\u00A0' : char;
                        span.style.cssText = `
                            display: inline-block;
                            opacity: 0;
                            transform: translateY(20px);
                            transition: opacity 0.4s ease, transform 0.4s ease;
                            transition-delay: ${index * 50}ms;
                        `;
                        title.appendChild(span);
                    });

                    // Trigger animation after a small delay
                    setTimeout(() => {
                        title.querySelectorAll('.letter').forEach(letter => {
                            letter.style.opacity = '1';
                            letter.style.transform = 'translateY(0)';
                        });
                    }, 100);
                }

                // Then grow divider lines
                const totalLetters = title ? title.querySelectorAll('.letter').length : 0;
                const dividerDelay = Math.max(300, totalLetters * 30);

                dividers.forEach((divider, index) => {
                    setTimeout(() => {
                        divider.classList.add('animate');
                    }, dividerDelay + (index * 100));
                });

                headerObserver.unobserve(header);
            }
        });
    }, { threshold: 0.3 });

    // Observe all pool headers
    document.querySelectorAll('.pool-header').forEach(header => {
        headerObserver.observe(header);
    });
}

// =============================================
// LENIS SMOOTH SCROLL
// =============================================

const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    orientation: 'vertical',
    gestureOrientation: 'vertical',
    smoothWheel: true,
    wheelMultiplier: 1,
    touchMultiplier: 2,
});

function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
}
requestAnimationFrame(raf);

// Update AOS on Lenis scroll
lenis.on('scroll', () => {
    AOS.refresh();
});

// Smooth scroll to anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;

        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            e.preventDefault();
            lenis.scrollTo(targetElement, {
                offset: 0,
                duration: 1.5,
                easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
            });
        }
    });
});

// =============================================
// SPLIT TEXT ANIMATION (Banner)
// =============================================

document.querySelectorAll('.split-text').forEach((element, elementIndex) => {
    const text = element.textContent.trim();
    const words = text.split(/\s+/);

    const computedStyle = window.getComputedStyle(element);
    const hasGradient = computedStyle.backgroundImage !== 'none';

    element.innerHTML = '';

    words.forEach((word, wordIndex) => {
        const span = document.createElement('span');
        span.className = 'word';
        span.textContent = word;

        let styles = `
            display: inline-block;
            opacity: 0;
            transform: translateY(30px);
            transition: opacity 1.5s ease, transform 1.5s ease;
            transition-delay: ${(elementIndex * 0.2) + (wordIndex * 0.1)}s;
        `;

        if (hasGradient) {
            styles += `
                background: ${computedStyle.backgroundImage};
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            `;
        }

        span.style.cssText = styles;
        element.appendChild(span);

        if (wordIndex < words.length - 1) {
            element.appendChild(document.createTextNode(' '));
        }
    });
});

function animateWords(element) {
    element.querySelectorAll('.word').forEach(word => {
        word.style.opacity = '1';
        word.style.transform = 'translateY(0)';
    });
}

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateWords(entry.target);
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.split-text').forEach(el => {
    observer.observe(el);
});

setTimeout(() => {
    document.querySelectorAll('.split-text').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
            animateWords(el);
        }
    });
}, 100);

// =============================================
// INITIALIZE ON DOM READY
// =============================================

document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    initContactForm();
});
