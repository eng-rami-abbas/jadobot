/**
 * JADO BOT - Physics Engine
 * Simulates realistic roulette ball physics
 */

class RoulettePhysics {
    constructor() {
        this.wheelRadius = 150;
        this.ballRadius = 8;
        this.pockets = 8;
        this.pocketAngle = (2 * Math.PI) / this.pockets;

        // Physics constants
        this.friction = 0.996;
        this.bounceDamping = 0.85;
        this.gravity = 0.15;
        this.minSpeed = 0.001;

        // Ball state
        this.ball = {
            angle: 0,
            radius: 140,
            speed: 0,
            angularSpeed: 0,
            bouncing: false,
            settled: false,
            pocket: null
        };

        // Wheel state
        this.wheel = {
            angle: 0,
            speed: 0,
            targetSpeed: 0
        };

        this.running = false;
        this.callbacks = {};
    }

    on(event, callback) {
        this.callbacks[event] = callback;
    }

    emit(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event](data);
        }
    }

    // Start the spin with target pocket
    startSpin(targetPocketIndex, wheelSpeed = 0.15, ballSpeed = 0.8) {
        this.running = true;

        // Wheel spins clockwise
        this.wheel.speed = wheelSpeed;
        this.wheel.targetSpeed = wheelSpeed;

        // Ball starts counter-clockwise (opposite to wheel)
        this.ball.angle = Math.random() * Math.PI * 2;
        this.ball.radius = 140;
        this.ball.speed = ballSpeed;
        this.ball.angularSpeed = -ballSpeed;
        this.ball.bouncing = false;
        this.ball.settled = false;
        this.ball.pocket = null;
        this.ball.targetPocket = targetPocketIndex;

        // Calculate target angle for the ball to land in the correct pocket
        const pocketCenterAngle = targetPocketIndex * this.pocketAngle + this.pocketAngle / 2;
        this.ball.targetAngle = pocketCenterAngle;

        this.emit('spinStart', { targetPocket: targetPocketIndex });

        this.simulate();
    }

    // Main physics simulation step
    simulate() {
        if (!this.running) return;

        // Update wheel
        this.wheel.angle += this.wheel.speed;
        this.wheel.speed *= this.friction;

        // Update ball
        this.updateBall();

        // Check if settled
        if (this.ball.settled) {
            this.running = false;
            this.emit('settled', { pocket: this.ball.pocket });
            return;
        }

        // Continue simulation
        requestAnimationFrame(() => this.simulate());
    }

    updateBall() {
        // Apply friction to ball speed
        this.ball.speed *= this.friction;

        // Update angular position
        this.ball.angle += this.ball.angularSpeed;

        // Ball spiraling inward
        if (this.ball.radius > 80) {
            this.ball.radius -= 0.3;
        }

        // Calculate relative angle to wheel
        const relativeAngle = this.ball.angle - this.wheel.angle;
        const normalizedAngle = ((relativeAngle % (2 * Math.PI)) + (2 * Math.PI)) % (2 * Math.PI);

        // Check for bounces against dividers
        const pocketEdge = this.pocketAngle / 2;
        const distanceToEdge = Math.abs((normalizedAngle % this.pocketAngle) - pocketEdge);

        if (distanceToEdge < 0.05 && this.ball.speed > 0.05) {
            // Bounce!
            this.ball.angularSpeed *= -this.bounceDamping;
            this.ball.speed *= this.bounceDamping;
            this.emit('bounce', { intensity: this.ball.speed });
        }

        // Check if ball is slow enough to settle
        if (this.ball.speed < this.minSpeed && this.ball.radius <= 85) {
            // Determine which pocket the ball is in
            const pocketIndex = Math.floor(normalizedAngle / this.pocketAngle) % this.pockets;
            this.ball.pocket = pocketIndex;
            this.ball.settled = true;

            // Snap to pocket center
            const pocketCenter = pocketIndex * this.pocketAngle + this.pocketAngle / 2;
            this.ball.angle = this.wheel.angle + pocketCenter;
            this.ball.radius = 75;
        }

        // Emit position update
        this.emit('ballUpdate', {
            angle: this.ball.angle,
            radius: this.ball.radius,
            speed: this.ball.speed,
            wheelAngle: this.wheel.angle
        });
    }

    // Get ball position in cartesian coordinates
    getBallPosition(centerX, centerY) {
        const x = centerX + Math.cos(this.ball.angle) * this.ball.radius;
        const y = centerY + Math.sin(this.ball.angle) * this.ball.radius;
        return { x, y };
    }

    // Get wheel rotation angle
    getWheelAngle() {
        return this.wheel.angle;
    }

    // Stop simulation
    stop() {
        this.running = false;
    }

    // Reset
    reset() {
        this.running = false;
        this.wheel.angle = 0;
        this.wheel.speed = 0;
        this.ball.angle = 0;
        this.ball.radius = 140;
        this.ball.speed = 0;
        this.ball.angularSpeed = 0;
        this.ball.bouncing = false;
        this.ball.settled = false;
        this.ball.pocket = null;
    }
}

// Global instance
window.roulettePhysics = new RoulettePhysics();
