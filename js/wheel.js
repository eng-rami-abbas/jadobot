/**
 * JADO BOT - 3D Wheel Engine
 * Uses Three.js + GSAP for premium 3D roulette wheel
 */

class Wheel3D {
    constructor() {
        this.container = document.getElementById('three-container');
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.wheelGroup = null;
        this.ballMesh = null;
        this.ledRing = null;
        this.particles = [];

        // Wheel configuration
        this.segments = [
            { name: '10000', color: '#8B0000', icon: '💵', textColor: '#FFD700' },
            { name: '20000', color: '#2D1B4E', icon: '💵', textColor: '#FFD700' },
            { name: 'حظ أوفر', color: '#8B0000', icon: '🍀', textColor: '#FFD700' },
            { name: 'Telegram Premium', color: '#2D1B4E', icon: '✈️', textColor: '#FFD700' },
            { name: '50000', color: '#8B0000', icon: '💵', textColor: '#FFD700' },
            { name: 'Bonus 5%', color: '#2D1B4E', icon: '🎁', textColor: '#FFD700' },
            { name: 'حظ أوفر', color: '#8B0000', icon: '🍀', textColor: '#FFD700' },
            { name: 'إعادة تدوير', color: '#2D1B4E', icon: '♻️', textColor: '#FFD700' }
        ];

        this.isVertical = true;
        this.isSpinning = false;
        this.animationId = null;

        this.init();
    }

    init() {
        // Scene setup
        this.scene = new THREE.Scene();

        // Camera
        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
        this.camera.position.set(0, 0, 500);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true, 
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        this.setupLighting();

        // Create wheel
        this.createWheel();

        // Create LED ring
        this.createLEDRing();

        // Create ball
        this.createBall();

        // Create particles
        this.createParticles();

        // Handle resize
        window.addEventListener('resize', () => this.onResize());

        // Start render loop
        this.animate();
    }

    setupLighting() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambientLight);

        // Main directional light (gold)
        const mainLight = new THREE.DirectionalLight(0xFFD700, 1.2);
        mainLight.position.set(100, 100, 200);
        mainLight.castShadow = true;
        mainLight.shadow.mapSize.width = 1024;
        mainLight.shadow.mapSize.height = 1024;
        this.scene.add(mainLight);

        // Rim light (purple)
        const rimLight = new THREE.PointLight(0x4B0082, 0.8, 400);
        rimLight.position.set(-150, -100, 100);
        this.scene.add(rimLight);

        // Fill light (warm)
        const fillLight = new THREE.PointLight(0xFFA500, 0.5, 300);
        fillLight.position.set(150, 50, 150);
        this.scene.add(fillLight);

        // Bottom glow
        const bottomLight = new THREE.PointLight(0xFFD700, 0.3, 200);
        bottomLight.position.set(0, -200, 50);
        this.scene.add(bottomLight);
    }

    createWheel() {
        this.wheelGroup = new THREE.Group();

        const radius = 150;
        const segments = 8;
        const angleStep = (Math.PI * 2) / segments;

        // Create segments
        for (let i = 0; i < segments; i++) {
            const segment = this.segments[i];
            const startAngle = i * angleStep;
            const endAngle = (i + 1) * angleStep;

            // Segment mesh
            const segmentShape = new THREE.Shape();
            segmentShape.moveTo(0, 0);
            segmentShape.arc(0, 0, radius, startAngle, endAngle, false);
            segmentShape.lineTo(0, 0);

            const segmentGeometry = new THREE.ExtrudeGeometry(segmentShape, {
                depth: 20,
                bevelEnabled: true,
                bevelThickness: 2,
                bevelSize: 2,
                bevelSegments: 3
            });

            const segmentMaterial = new THREE.MeshStandardMaterial({
                color: new THREE.Color(segment.color),
                metalness: 0.6,
                roughness: 0.3,
                emissive: new THREE.Color(segment.color),
                emissiveIntensity: 0.1
            });

            const segmentMesh = new THREE.Mesh(segmentGeometry, segmentMaterial);
            segmentMesh.castShadow = true;
            segmentMesh.receiveShadow = true;
            this.wheelGroup.add(segmentMesh);

            // Gold border for segment
            const borderShape = new THREE.Shape();
            borderShape.moveTo(0, 0);
            borderShape.arc(0, 0, radius + 2, startAngle, endAngle, false);
            borderShape.arc(0, 0, radius + 5, endAngle, startAngle, true);
            borderShape.lineTo(0, 0);

            const borderGeometry = new THREE.ExtrudeGeometry(borderShape, {
                depth: 22,
                bevelEnabled: false
            });

            const borderMaterial = new THREE.MeshStandardMaterial({
                color: 0xFFD700,
                metalness: 1.0,
                roughness: 0.1,
                emissive: 0xFFD700,
                emissiveIntensity: 0.3
            });

            const borderMesh = new THREE.Mesh(borderGeometry, borderMaterial);
            this.wheelGroup.add(borderMesh);

            // Text label
            const midAngle = startAngle + angleStep / 2;
            const textRadius = radius * 0.65;
            const textX = Math.cos(midAngle) * textRadius;
            const textY = Math.sin(midAngle) * textRadius;

            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');

            ctx.fillStyle = 'transparent';
            ctx.fillRect(0, 0, 256, 128);

            ctx.font = 'bold 36px Arial';
            ctx.fillStyle = segment.textColor;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.shadowColor = '#FFD700';
            ctx.shadowBlur = 10;
            ctx.fillText(segment.icon + ' ' + segment.name, 128, 64);

            const textTexture = new THREE.CanvasTexture(canvas);
            const textMaterial = new THREE.MeshBasicMaterial({
                map: textTexture,
                transparent: true,
                side: THREE.DoubleSide
            });

            const textGeometry = new THREE.PlaneGeometry(80, 40);
            const textMesh = new THREE.Mesh(textGeometry, textMaterial);
            textMesh.position.set(textX, textY, 22);
            textMesh.rotation.z = midAngle - Math.PI / 2;
            this.wheelGroup.add(textMesh);
        }

        // Outer gold ring
        const ringGeometry = new THREE.TorusGeometry(radius + 8, 6, 16, 100);
        const ringMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFD700,
            metalness: 1.0,
            roughness: 0.1,
            emissive: 0xFFD700,
            emissiveIntensity: 0.2
        });
        const ringMesh = new THREE.Mesh(ringGeometry, ringMaterial);
        this.wheelGroup.add(ringMesh);

        // Inner gold ring
        const innerRingGeometry = new THREE.TorusGeometry(40, 4, 16, 50);
        const innerRingMesh = new THREE.Mesh(innerRingGeometry, ringMaterial.clone());
        this.wheelGroup.add(innerRingMesh);

        // Center hub
        const hubGeometry = new THREE.CylinderGeometry(35, 35, 25, 32);
        const hubMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            metalness: 0.9,
            roughness: 0.2
        });
        const hubMesh = new THREE.Mesh(hubGeometry, hubMaterial);
        hubMesh.rotation.x = Math.PI / 2;
        hubMesh.position.z = 12;
        this.wheelGroup.add(hubMesh);

        // Center gold accent
        const centerAccentGeometry = new THREE.CylinderGeometry(30, 30, 26, 32);
        const centerAccentMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFD700,
            metalness: 1.0,
            roughness: 0.1
        });
        const centerAccentMesh = new THREE.Mesh(centerAccentGeometry, centerAccentMaterial);
        centerAccentMesh.rotation.x = Math.PI / 2;
        centerAccentMesh.position.z = 12;
        this.wheelGroup.add(centerAccentMesh);

        this.scene.add(this.wheelGroup);
    }

    createLEDRing() {
        this.ledRing = new THREE.Group();
        const ledCount = 32;
        const radius = 165;

        for (let i = 0; i < ledCount; i++) {
            const angle = (i / ledCount) * Math.PI * 2;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;

            const ledGeometry = new THREE.SphereGeometry(3, 8, 8);
            const ledMaterial = new THREE.MeshStandardMaterial({
                color: 0xFFD700,
                emissive: 0xFFD700,
                emissiveIntensity: 0.5
            });

            const led = new THREE.Mesh(ledGeometry, ledMaterial);
            led.position.set(x, y, 25);
            led.userData.index = i;
            led.userData.baseIntensity = 0.3 + Math.random() * 0.4;
            this.ledRing.add(led);
        }

        this.wheelGroup.add(this.ledRing);
    }

    createBall() {
        const ballGeometry = new THREE.SphereGeometry(8, 32, 32);
        const ballMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFD700,
            metalness: 1.0,
            roughness: 0.1,
            emissive: 0xFFA500,
            emissiveIntensity: 0.3
        });

        this.ballMesh = new THREE.Mesh(ballGeometry, ballMaterial);
        this.ballMesh.position.set(140, 0, 30);
        this.ballMesh.castShadow = true;
        this.scene.add(this.ballMesh);
    }

    createParticles() {
        const particleCount = 50;
        const particleGeometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 600;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 600;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 200;
        }

        particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const particleMaterial = new THREE.PointsMaterial({
            color: 0xFFD700,
            size: 3,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });

        this.particleSystem = new THREE.Points(particleGeometry, particleMaterial);
        this.scene.add(this.particleSystem);
    }

    // Animate from vertical to horizontal
    async animateToHorizontal() {
        return new Promise(resolve => {
            gsap.to(this.wheelGroup.rotation, {
                x: Math.PI / 2,
                y: 0,
                z: 0,
                duration: 2,
                ease: 'power2.inOut',
                onComplete: () => {
                    this.isVertical = false;
                    resolve();
                }
            });

            // Camera zoom
            gsap.to(this.camera.position, {
                z: 350,
                duration: 2,
                ease: 'power2.inOut'
            });
        });
    }

    // Animate from horizontal to vertical
    async animateToVertical() {
        return new Promise(resolve => {
            gsap.to(this.wheelGroup.rotation, {
                x: 0,
                y: 0,
                z: 0,
                duration: 1.5,
                ease: 'power2.inOut',
                onComplete: () => {
                    this.isVertical = true;
                    resolve();
                }
            });

            gsap.to(this.camera.position, {
                z: 500,
                duration: 1.5,
                ease: 'power2.inOut'
            });
        });
    }

    // Spin the wheel
    spinWheel(targetAngle, duration = 5000) {
        this.isSpinning = true;

        const currentRotation = this.wheelGroup.rotation.z;
        const spins = 5 + Math.floor(Math.random() * 3);
        const targetRotation = currentRotation + (spins * Math.PI * 2) + targetAngle;

        gsap.to(this.wheelGroup.rotation, {
            z: targetRotation,
            duration: duration / 1000,
            ease: 'power4.out',
            onComplete: () => {
                this.isSpinning = false;
            }
        });
    }

    // Update ball position
    updateBallPosition(angle, radius, z = 30) {
        if (this.ballMesh) {
            this.ballMesh.position.x = Math.cos(angle) * radius;
            this.ballMesh.position.y = Math.sin(angle) * radius;
            this.ballMesh.position.z = z;
        }
    }

    // Animate LEDs
    animateLEDs(time) {
        if (!this.ledRing) return;

        this.ledRing.children.forEach((led, i) => {
            const intensity = led.userData.baseIntensity + 
                Math.sin(time * 3 + i * 0.5) * 0.3;
            led.material.emissiveIntensity = Math.max(0.1, intensity);

            // Chase effect
            const chaseIndex = Math.floor(time * 8) % this.ledRing.children.length;
            if (i === chaseIndex) {
                led.material.emissiveIntensity = 1.0;
            }
        });
    }

    // Animate particles
    animateParticles(time) {
        if (!this.particleSystem) return;

        const positions = this.particleSystem.geometry.attributes.position.array;
        for (let i = 0; i < positions.length; i += 3) {
            positions[i + 1] += Math.sin(time + i) * 0.2;
            if (positions[i + 1] > 300) positions[i + 1] = -300;
        }
        this.particleSystem.geometry.attributes.position.needsUpdate = true;
        this.particleSystem.rotation.y = time * 0.1;
    }

    // Shake animation
    shake() {
        gsap.to(this.wheelGroup.position, {
            x: 5,
            duration: 0.05,
            yoyo: true,
            repeat: 5,
            ease: 'power1.inOut'
        });
    }

    // Flash gold
    flashGold() {
        const originalIntensity = {};
        this.wheelGroup.traverse(child => {
            if (child.material && child.material.emissive) {
                originalIntensity[child.uuid] = child.material.emissiveIntensity;
                gsap.to(child.material, {
                    emissiveIntensity: 2,
                    duration: 0.1,
                    yoyo: true,
                    repeat: 5,
                    onComplete: () => {
                        child.material.emissiveIntensity = originalIntensity[child.uuid] || 0;
                    }
                });
            }
        });
    }

    // Zoom camera
    zoomCamera(factor, duration = 0.8) {
        gsap.to(this.camera.position, {
            z: 500 * factor,
            duration: duration,
            ease: 'power2.inOut'
        });
    }

    // Main animation loop
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        const time = performance.now() * 0.001;

        // Animate LEDs
        this.animateLEDs(time);

        // Animate particles
        this.animateParticles(time);

        // Subtle wheel float
        if (!this.isSpinning && this.wheelGroup) {
            this.wheelGroup.position.y = Math.sin(time * 0.5) * 3;
        }

        this.renderer.render(this.scene, this.camera);
    }

    // Resize handler
    onResize() {
        const aspect = window.innerWidth / window.innerHeight;
        this.camera.aspect = aspect;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // Get segment at angle
    getSegmentAtAngle(angle) {
        const normalized = ((angle % (Math.PI * 2)) + (Math.PI * 2)) % (Math.PI * 2);
        const segmentIndex = Math.floor(normalized / ((Math.PI * 2) / 8));
        return this.segments[segmentIndex % 8];
    }

    // Cleanup
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.renderer.dispose();
        this.container.removeChild(this.renderer.domElement);
    }
}

// Global instance
window.wheel3D = null;
