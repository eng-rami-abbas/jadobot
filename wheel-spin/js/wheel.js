/**
 * JADO BOT - 3D Wheel Engine (Three.js)
 * Falls back gracefully if Three.js not available
 */

class Wheel3D {
    constructor() {
        this.container = document.getElementById('three-container');
        if (!this.container) {
            console.warn('Three.js container not found');
            return;
        }

        // Check if THREE is available
        if (typeof THREE === 'undefined') {
            console.warn('Three.js not loaded, 3D wheel disabled');
            this.container.style.display = 'none';
            return;
        }

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.wheelGroup = null;
        this.ballMesh = null;
        this.ledRing = null;
        this.animationId = null;
        this.isReady = false;

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

        try {
            this.init();
            this.isReady = true;
        } catch (e) {
            console.error('3D wheel init failed:', e);
            this.container.style.display = 'none';
        }
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();

        // Camera
        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
        this.camera.position.set(0, 0, 400);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true, 
            alpha: true
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        this.setupLighting();

        // Create wheel
        this.createWheel();

        // Create ball
        this.createBall();

        // Handle resize
        window.addEventListener('resize', () => this.onResize());

        // Start render loop
        this.animate();
    }

    setupLighting() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        const mainLight = new THREE.DirectionalLight(0xFFD700, 1.0);
        mainLight.position.set(100, 100, 200);
        this.scene.add(mainLight);

        const rimLight = new THREE.PointLight(0x4B0082, 0.6, 400);
        rimLight.position.set(-150, -100, 100);
        this.scene.add(rimLight);
    }

    createWheel() {
        this.wheelGroup = new THREE.Group();

        const radius = 150;
        const segments = 8;
        const angleStep = (Math.PI * 2) / segments;

        for (let i = 0; i < segments; i++) {
            const segment = this.segments[i];
            const startAngle = i * angleStep;
            const endAngle = (i + 1) * angleStep;

            // Create segment using shape
            const shape = new THREE.Shape();
            shape.moveTo(0, 0);
            shape.arc(0, 0, radius, startAngle, endAngle, false);
            shape.lineTo(0, 0);

            const geometry = new THREE.ShapeGeometry(shape);
            const material = new THREE.MeshStandardMaterial({
                color: new THREE.Color(segment.color),
                metalness: 0.5,
                roughness: 0.4,
                side: THREE.DoubleSide
            });

            const mesh = new THREE.Mesh(geometry, material);
            this.wheelGroup.add(mesh);

            // Text label
            const midAngle = startAngle + angleStep / 2;
            const textR = radius * 0.6;

            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = 'transparent';
            ctx.fillRect(0, 0, 256, 128);
            ctx.font = 'bold 32px Arial';
            ctx.fillStyle = segment.textColor;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(segment.icon + ' ' + segment.name, 128, 64);

            const texture = new THREE.CanvasTexture(canvas);
            const textMat = new THREE.MeshBasicMaterial({
                map: texture,
                transparent: true,
                side: THREE.DoubleSide
            });

            const textGeo = new THREE.PlaneGeometry(70, 35);
            const textMesh = new THREE.Mesh(textGeo, textMat);
            textMesh.position.set(
                Math.cos(midAngle) * textR,
                Math.sin(midAngle) * textR,
                2
            );
            textMesh.rotation.z = midAngle - Math.PI / 2;
            this.wheelGroup.add(textMesh);
        }

        // Outer ring
        const ringGeo = new THREE.TorusGeometry(radius + 5, 4, 16, 100);
        const ringMat = new THREE.MeshStandardMaterial({
            color: 0xFFD700,
            metalness: 0.9,
            roughness: 0.1
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        this.wheelGroup.add(ring);

        // Center hub
        const hubGeo = new THREE.CircleGeometry(30, 32);
        const hubMat = new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            metalness: 0.8,
            roughness: 0.2
        });
        const hub = new THREE.Mesh(hubGeo, hubMat);
        hub.position.z = 1;
        this.wheelGroup.add(hub);

        this.scene.add(this.wheelGroup);
    }

    createBall() {
        const ballGeo = new THREE.SphereGeometry(6, 16, 16);
        const ballMat = new THREE.MeshStandardMaterial({
            color: 0xFFD700,
            metalness: 1.0,
            roughness: 0.1
        });

        this.ballMesh = new THREE.Mesh(ballGeo, ballMat);
        this.ballMesh.position.set(130, 0, 10);
        this.scene.add(this.ballMesh);
    }

    updateBallPosition(angle, radius, z = 10) {
        if (this.ballMesh) {
            this.ballMesh.position.x = Math.cos(angle) * radius;
            this.ballMesh.position.y = Math.sin(angle) * radius;
            this.ballMesh.position.z = z;
        }
    }

    setWheelRotation(angle) {
        if (this.wheelGroup) {
            this.wheelGroup.rotation.z = angle;
        }
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        if (this.wheelGroup) {
            // Subtle floating animation
            this.wheelGroup.position.y = Math.sin(Date.now() * 0.001) * 2;
        }

        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        if (!this.camera || !this.renderer) return;
        const aspect = window.innerWidth / window.innerHeight;
        this.camera.aspect = aspect;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.renderer) {
            this.renderer.dispose();
        }
    }
}

// Global instance placeholder
window.wheel3D = null;
