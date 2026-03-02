document.addEventListener('DOMContentLoaded', () => {

    // Smooth Scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Elements
    const generateBtn = document.getElementById('generateBtn');
    const videoUrlInput = document.getElementById('videoUrlInput');
    const dropArea = document.getElementById('dropArea');
    const processingOverlay = document.getElementById('processingOverlay');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('processingStatus');

    // Processing steps logic
    const startProcessing = () => {
        if (!videoUrlInput.value && event.target === generateBtn) {
            alert('Please paste a YouTube URL first!');
            return;
        }

        processingOverlay.classList.add('active');

        let progress = 0;
        let currentStep = 1;

        // Reset Steps UI
        document.querySelectorAll('.step').forEach((el, index) => {
            if (index < 2) {
                el.classList.remove('active', 'pending');
                el.classList.add('pending');
                el.innerHTML = '<i class="fa-regular fa-circle"></i> ' + el.innerText.trim();
            } else {
                el.classList.add('pending');
                el.innerHTML = '<i class="fa-regular fa-circle"></i> ' + el.innerText.trim();
            }
        });

        const stepsData = [
            { text: "Downloading raw video...", time: 20 },
            { text: "AI is finding viral hooks...", time: 45 },
            { text: "Generating dynamic captions...", time: 70 },
            { text: "Applying smart tracking & rendering...", time: 95 }
        ];

        const interval = setInterval(() => {
            progress += 0.5;
            progressBar.style.width = `${progress}%`;

            // Update Steps
            const stepIndex = stepsData.findIndex(s => progress <= s.time);

            if (stepIndex !== -1 && currentStep !== stepIndex) {
                currentStep = stepIndex;
                statusText.innerText = stepsData[stepIndex].text;

                const stepEls = document.querySelectorAll('.step');
                if (stepIndex > 0) {
                    // Mark previous as complete
                    stepEls[stepIndex - 1].innerHTML = '<i class="fa-solid fa-check"></i> ' + stepEls[stepIndex - 1].innerText.trim();
                    stepEls[stepIndex - 1].classList.add('active');
                    stepEls[stepIndex - 1].classList.remove('pending');
                }

                // Set current as processing
                stepEls[stepIndex].innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> ' + stepEls[stepIndex].innerText.trim();
            }

            if (progress >= 100) {
                clearInterval(interval);
                statusText.innerText = "Clips Ready! Redirecting...";
                setTimeout(() => {
                    processingOverlay.classList.remove('active');
                    alert("Success! In a real application, you would be redirected to the editor dashboard.");
                    videoUrlInput.value = '';
                    progressBar.style.width = '0%';
                }, 1000);
            }
        }, 50); // 10 seconds total simulation
    };

    generateBtn.addEventListener('click', startProcessing);

    // Drag and Drop Effects
    dropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = "var(--accent-1)";
        dropArea.style.background = "rgba(247, 37, 133, 0.1)";
    });

    dropArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = "var(--border-color)";
        dropArea.style.background = "rgba(255,255,255,0.01)";
    });

    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = "var(--border-color)";
        dropArea.style.background = "rgba(255,255,255,0.01)";
        if (e.dataTransfer.files.length > 0) {
            startProcessing();
        }
    });

    dropArea.addEventListener('click', () => {
        // Trigger a fake file upload flow
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'video/*';
        fileInput.onchange = () => {
            if (fileInput.files.length > 0) startProcessing();
        };
        fileInput.click();
    });

    // Glowing Cursor Effect (subtle)
    document.addEventListener('mousemove', (e) => {
        const glow = document.querySelector('.hero-bg-glow');
        if (glow) {
            const x = e.clientX;
            const y = e.clientY + window.scrollY; // adjust for scroll
            // Only move if near hero
            if (window.scrollY < window.innerHeight) {
                glow.style.transform = `translate(calc(-50% + ${(x - window.innerWidth / 2) * 0.1}px), calc(-50% + ${(y - window.innerHeight / 2) * 0.1}px))`;
            }
        }
    });
});
