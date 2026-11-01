import turtle
import random

# Game Settings
DELAY = 150 # milliseconds

# State
score = 0
high_score = 0

# Set up the screen
wn = turtle.Screen()
wn.title("Snake Game")
wn.bgcolor("green")
wn.setup(width=650, height=750)
wn.tracer(0)

# Draw playing area border
border = turtle.Turtle()
border.speed(0)
border.color("white")
border.penup()
border.goto(-310, -310)
border.pendown()
border.pensize(2)
for _ in range(4):
    border.forward(620)
    border.left(90)
border.hideturtle()

# Snake head
head = turtle.Turtle()
head.speed(0)
head.shape("square")
head.color("red")
head.penup()
head.goto(0, 0)
head.direction = "stop"

# Snake food
food = turtle.Turtle()
food.speed(0)
food.shape("circle")
food.color("yellow")
food.penup()
food.goto(0, 100)

segments = []
direction_queue = []

# Pen for scoring
pen = turtle.Turtle()
pen.speed(0)
pen.shape("square")
pen.color("white")
pen.penup()
pen.hideturtle()
pen.goto(0, 320)
pen.write("Score: 0  High Score: 0", align="center", font=("Courier", 24, "normal"))

def go_up():
    if len(direction_queue) == 0:
        if head.direction != "down" and head.direction != "up":
            direction_queue.append("up")
    elif direction_queue[-1] != "down" and direction_queue[-1] != "up":
        direction_queue.append("up")

def go_down():
    if len(direction_queue) == 0:
        if head.direction != "up" and head.direction != "down":
            direction_queue.append("down")
    elif direction_queue[-1] != "up" and direction_queue[-1] != "down":
        direction_queue.append("down")

def go_left():
    if len(direction_queue) == 0:
        if head.direction != "right" and head.direction != "left":
            direction_queue.append("left")
    elif direction_queue[-1] != "right" and direction_queue[-1] != "left":
        direction_queue.append("left")

def go_right():
    if len(direction_queue) == 0:
        if head.direction != "left" and head.direction != "right":
            direction_queue.append("right")
    elif direction_queue[-1] != "left" and direction_queue[-1] != "right":
        direction_queue.append("right")

def move():
    if head.direction == "up":
        head.sety(head.ycor() + 20)
    elif head.direction == "down":
        head.sety(head.ycor() - 20)
    elif head.direction == "left":
        head.setx(head.xcor() - 20)
    elif head.direction == "right":
        head.setx(head.xcor() + 20)

def reset_game():
    global score, DELAY
    head.goto(0, 0)
    head.direction = "stop"
    
    # Hide segments
    for segment in segments:
        segment.goto(1000, 1000)
    segments.clear()
    direction_queue.clear()
    
    score = 0
    DELAY = 150
    update_score()

def update_score():
    pen.clear()
    pen.write(f"Score: {score}  High Score: {high_score}", align="center", font=("Courier", 24, "normal"))

def game_loop():
    global score, high_score, DELAY

    wn.update()

    # Food collision
    if head.distance(food) < 20:
        x = random.randint(-14, 14) * 20
        y = random.randint(-14, 14) * 20
        food.goto(x, y)

        new_segment = turtle.Turtle()
        new_segment.speed(0)
        new_segment.shape("square")
        new_segment.color("darkred")
        new_segment.penup()
        segments.append(new_segment)

        score += 10
        if score > high_score:
            high_score = score
        
        if DELAY > 20:
            DELAY -= 2

        update_score()

    # Move body segments
    for index in range(len(segments) - 1, 0, -1):
        x = segments[index - 1].xcor()
        y = segments[index - 1].ycor()
        segments[index].goto(x, y)

    # Move neck to head
    if len(segments) > 0:
        segments[0].goto(head.xcor(), head.ycor())

    # Apply next direction from the queue
    if len(direction_queue) > 0:
        head.direction = direction_queue.pop(0)

    move()

    # Border wrap (apply after moving)
    if head.xcor() > 300:
        head.setx(-300)
    elif head.xcor() < -300:
        head.setx(300)

    if head.ycor() > 300:
        head.sety(-300)
    elif head.ycor() < -300:
        head.sety(300)

    # Body collision
    for segment in segments:
        if segment.distance(head) < 20:
            reset_game()

    wn.ontimer(game_loop, DELAY)

# Keybindings
wn.listen()
wn.onkeypress(go_up, "w")
wn.onkeypress(go_down, "s")
wn.onkeypress(go_left, "a")
wn.onkeypress(go_right, "d")
wn.onkeypress(go_up, "Up")
wn.onkeypress(go_down, "Down")
wn.onkeypress(go_left, "Left")
wn.onkeypress(go_right, "Right")

# Start game loop
game_loop()
wn.mainloop()