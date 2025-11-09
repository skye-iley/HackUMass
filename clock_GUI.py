import datetime
import pygame
import asyncio
import time

def play_mp3(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    # Keep the program running until the music finishes
    """
    while pygame.mixer.music.get_busy():
        time.sleep(1)
    """
    # Replace 'your_song.mp3' with the actual path to your MP3 file

async def view_clock(queue):
    pygame.init()
    pygame.mixer.init()

    background_grey = (37, 36, 46)
    #white = (255, 255, 255)
    def_text_color = (136, 143, 142)
    green = (0, 255, 0)
    blue = (0, 0, 255)
    #red = (255,0,0)

    # assigning values to X and Y variable
    X = 800
    Y = 400

    # create the display surface object
    # of specific dimension..e(X, Y).
    display_surface = pygame.display.set_mode((X, Y))

    # set the pygame window name
    pygame.display.set_caption('Clock')

    # create a font object.
    # 1st parameter is the font file
    # which is present in pygame.
    # 2nd parameter is size of the font
    font = pygame.font.Font('freesansbold.ttf', 100)

    # create a text surface object,
    # on which text is drawn on it.
    text = font.render(datetime.datetime.now().isoformat()[11:19], True, def_text_color, background_grey)

    # create a rectangular object for the
    # text surface object
    textRect = text.get_rect()
    print

    # set the center of the rectangular object.
    textRect.center = (X // 2, Y // 2)
    clock = pygame.time.Clock()
    # infinite loop
    Alarmflag = 0
    timercounter = 0
    metacounter = 0
    colorFlag = 0
    curColor = def_text_color
    while True:
        try:
            message = queue.get_nowait()
            if message == "ALARM TIME":
                Alarmflag = 1
                colorFlag = 1
                timercounter = 0
                #curColor = green
                play_mp3('output.mp3')
        except:
            pass

        if Alarmflag == 1:
            if timercounter > 60:
                colorFlag = not colorFlag
                timercounter = 0
                metacounter += 1
                
            if colorFlag:
                curColor = green
            else:
                curColor = def_text_color
            if metacounter > 60:
                metacounter = 0
                Alarmflag = 0
                curColor = def_text_color

        # completely fill the surface object
        # with white color
        display_surface.fill(background_grey)

        # copying the text surface object
        # to the display surface object
        # at the center coordinate.
        text = font.render(datetime.datetime.now().isoformat()[11:19], True, curColor, background_grey)
        display_surface.blit(text, textRect)

        # iterate over the list of Event objects
        # that was returned by pygame.event.get() method.
        for event in pygame.event.get():

            # if event object type is QUIT
            # then quitting the pygame
            # and program both.
            if event.type == pygame.QUIT:

                # deactivates the pygame library
                pygame.quit()
                return None
                # quit the program.
                #quit()

        # Draws the surface object to the screen.
        pygame.display.update()

        await asyncio.sleep(0)
        timercounter += 1
        clock.tick(60)


if __name__ == "__main__":
    asyncio.run(view_clock())