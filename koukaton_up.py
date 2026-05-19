import pygame
import sys
import os
import random

# カレントディレクトリの固定
os.chdir(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 600, 800
FPS = 60
GRAVITY = 0.6

BLACK = (20, 20, 25)
BLUE = (100, 150, 255)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)

# ギミック床の色定義
COLOR_NORMAL = (120, 120, 120)       # 緑（通常）
COLOR_FAKE = (180, 0, 180)           # 紫（すり抜ける）
COLOR_ICE = (100, 200, 255)          # 水色（滑る）
COLOR_TRAMPOLINE = (255, 140, 0)     # オレンジ（大ジャンプ）
COLOR_TRAP = (255, 50, 50)           # 赤（最初に戻る）
COLOR_RED_UI = (255, 100, 100)       # UI用赤

# ==========================================
# 1. データ構造（クラス）の定義
# ==========================================

class Player:
    def __init__(self):
        self._image = pygame.Surface((30, 40))
        self._image.fill(BLUE)
        self._rect = self._image.get_rect(center=(WIDTH // 2, HEIGHT - 100))
        
        self._vel_x = 0
        self._vel_y = 0
        self._on_ground = False
        
        self._is_charging = False
        self._charge_power = 0
        self._max_charge = 20.0
        self._direction = 1
        
        self._is_clear = False
        self._on_ice = False      # 氷の上にいるかどうかのフラグ
        self._is_reset = False    # トラップで初期位置に戻されたかどうかのフラグ

    # --- ゲッター ---
    def get_image(self): return self._image
    def get_rect(self): return self._rect
    def get_vel_x(self): return self._vel_x
    def get_vel_y(self): return self._vel_y
    def get_on_ground(self): return self._on_ground
    def get_is_charging(self): return self._is_charging
    def get_charge_power(self): return self._charge_power
    def get_max_charge(self): return self._max_charge
    def get_direction(self): return self._direction
    def get_is_clear(self): return self._is_clear
    def get_on_ice(self): return self._on_ice
    def get_is_reset(self): return self._is_reset

    # --- セッター ---
    def set_vel_x(self, value): self._vel_x = value
    def set_vel_y(self, value): self._vel_y = value
    def set_on_ground(self, value): self._on_ground = value
    def set_is_charging(self, value): self._is_charging = value
    def set_charge_power(self, value): self._charge_power = value
    def set_direction(self, value): self._direction = value
    def set_is_clear(self, value): self._is_clear = value
    def set_on_ice(self, value): self._on_ice = value
    def set_is_reset(self, value): self._is_reset = value


class Platform:
    # ギミック判定用に plat_type（床の種類）を追加
    def __init__(self, x, y, w, h, color, plat_type="normal"):
        self._image = pygame.Surface((w, h))
        self._image.fill(color)
        self._rect = self._image.get_rect(topleft=(x, y))
        self._type = plat_type

    # ゲッター
    def get_image(self): return self._image
    def get_rect(self): return self._rect
    def get_type(self): return self._type


# ==========================================
# 2. クラスを操作する関数
# ==========================================

def update_player(player, keys, platforms, goal_block):
    """プレイヤーの物理挙動と状態を更新する関数"""
    
    if not player.get_is_clear():
        # 1. 地面にいる時の処理
        if player.get_on_ground():
            
            # 氷の上の場合はツルツル滑らせる（慣性を残す）、通常はピタッと止まる
            if player.get_on_ice():
                player.set_vel_x(player.get_vel_x() * 0.96) # 摩擦で少しずつ減速
            else:
                player.set_vel_x(0)
            
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.set_direction(-1)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.set_direction(1)

            if keys[pygame.K_SPACE]:
                player.set_is_charging(True)
                current_power = player.get_charge_power()
                if current_power < player.get_max_charge():
                    player.set_charge_power(current_power + 0.4)
            else:
                if player.get_is_charging():
                    power = player.get_charge_power()
                    direction = player.get_direction()
                    
                    player.set_vel_y(-power * 0.9 - 5)
                    player.set_vel_x(direction * (power * 0.4 + 2))
                    
                    player.set_is_charging(False)
                    player.set_charge_power(0)
                    player.set_on_ground(False)
                    player.set_on_ice(False)
    
    # 2. 重力の適用
    if not player.get_on_ground():
        player.set_vel_y(player.get_vel_y() + GRAVITY)

    rect = player.get_rect()

    # 座標の更新 (X軸) と壁の跳ね返り
    rect.x += player.get_vel_x()
    if rect.left < 0:
        rect.left = 0
        player.set_vel_x(player.get_vel_x() * -0.5)
        player.set_direction(1)
    if rect.right > WIDTH:
        rect.right = WIDTH
        player.set_vel_x(player.get_vel_x() * -0.5)
        player.set_direction(-1)

    # 座標の更新 (Y軸)
    rect.y += int(player.get_vel_y())

    # 3. ゴール（天井）との当たり判定
    goal_rect = goal_block.get_rect()
    if rect.colliderect(goal_rect):
        if player.get_vel_y() < 0:
            rect.top = goal_rect.bottom
            player.set_vel_y(0)
            player.set_is_clear(True)

    # 4. 足場との当たり判定
    player.set_on_ground(False)
    player.set_on_ice(False)

    if player.get_vel_y() > 0:
        for plat in platforms:
            # ギミック：フェイク床の場合は当たり判定を無視してすり抜ける
            if plat.get_type() == "fake":
                continue
                
            plat_rect = plat.get_rect()
            if rect.colliderect(plat_rect):
                if rect.bottom <= plat_rect.top + player.get_vel_y() + 1:
                    
                    # ギミック：トランポリン床
                    if plat.get_type() == "trampoline":
                        rect.bottom = plat_rect.top
                        player.set_vel_y(-25) # 大ジャンプ
                        player.set_on_ground(False)
                        break
                    
                    # ギミック：スタートに戻る罠床
                    if plat.get_type() == "trap":
                        rect.center = (WIDTH // 2, HEIGHT - 100) # 初期座標へ転送
                        player.set_vel_y(0)
                        player.set_vel_x(0)
                        player.set_is_reset(True) # カメラリセット用のフラグを立てる
                        break

                    # 通常の着地処理
                    rect.bottom = plat_rect.top
                    player.set_vel_y(0)
                    player.set_on_ground(True)
                    
                    # ギミック：氷床
                    if plat.get_type() == "ice":
                        player.set_on_ice(True)
                    else:
                        player.set_vel_x(0)
                    break


# ==========================================
# 3. メインループ
# ==========================================

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Jump King - Gimmick Floors")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    large_font = pygame.font.SysFont(None, 72)

    player = Player()
    platforms = []
    
    # --- 10層分のマップ生成（階層ごとにギミックを割り当て） ---
    platforms.append(Platform(0, HEIGHT - 40, WIDTH, 40, COLOR_NORMAL, "normal")) # スタート床

    TOTAL_FLOORS = 10
    goal_y = (HEIGHT - 40) - (HEIGHT * TOTAL_FLOORS)
    goal_block = Platform(0, goal_y, WIDTH, 40, GOLD, "goal")

    for f in range(TOTAL_FLOORS):
        floor_bottom = HEIGHT - (f * HEIGHT)
        floor_top = HEIGHT - ((f + 1) * HEIGHT)
        
        floor_plats = []
        plat_y = floor_bottom - 150
        
        # 1つの階層につき、上に向かってランダムに足場を生成
        while plat_y > floor_top + 50:
            w = random.randint(60, 130)
            x = random.randint(0, WIDTH - w)
            floor_plats.append(Platform(x, plat_y, w, 20, COLOR_NORMAL, "normal"))
            gap_y = random.randint(80, 130)
            plat_y -= gap_y
            
        # --- ギミック床の割り当て ---
        # 足場が4つ以上ある場合のみ、ランダムな足場を選んでギミックに差し替える
        if len(floor_plats) >= 4:
            specials = random.sample(range(len(floor_plats)), 4)
            
            # 1. すり抜ける床（紫）を1つ生成
            p_fake = floor_plats[specials[0]]
            floor_plats[specials[0]] = Platform(p_fake.get_rect().x, p_fake.get_rect().y, p_fake.get_rect().width, 20, COLOR_FAKE, "fake")
            
            # 2. 滑る床（水色）を1つ生成
            p_ice = floor_plats[specials[1]]
            floor_plats[specials[1]] = Platform(p_ice.get_rect().x, p_ice.get_rect().y, p_ice.get_rect().width, 20, COLOR_ICE, "ice")
            
            # 3. トランポリン（オレンジ）を1つ生成
            p_tramp = floor_plats[specials[2]]
            floor_plats[specials[2]] = Platform(p_tramp.get_rect().x, p_tramp.get_rect().y, p_tramp.get_rect().width, 20, COLOR_TRAMPOLINE, "trampoline")
            
            # 4. 最上層(f == 9)のみ、スタートに戻る罠床（赤）を生成
            if f == TOTAL_FLOORS - 1:
                p_trap = floor_plats[specials[3]]
                floor_plats[specials[3]] = Platform(p_trap.get_rect().x, p_trap.get_rect().y, p_trap.get_rect().width, 20, COLOR_TRAP, "trap")
                
        platforms.extend(floor_plats)

    camera_y = 0
    max_height = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        
        # 関数呼び出し
        update_player(player, keys, platforms, goal_block)

        p_rect = player.get_rect()

        # --- トラップ床で戻された場合のカメラリセット ---
        if player.get_is_reset():
            camera_y = 0
            player.set_is_reset(False) # フラグを元に戻す

        # --- 通常のカメラ処理 ---
        SCROLL_TOP_MARGIN = 200
        if p_rect.y - camera_y < SCROLL_TOP_MARGIN:
            camera_y = p_rect.y - SCROLL_TOP_MARGIN

        SCROLL_BOTTOM_MARGIN = 150
        camera_easing_down = 0.08
        if p_rect.bottom - camera_y > HEIGHT - SCROLL_BOTTOM_MARGIN:
            target_camera_y = p_rect.bottom - (HEIGHT - SCROLL_BOTTOM_MARGIN)
            camera_y += (target_camera_y - camera_y) * camera_easing_down

        if camera_y > 0:
            camera_y = 0

        # --- スコア・階層計算 ---
        current_height = (HEIGHT - 40) - p_rect.bottom
        if current_height > max_height:
            max_height = current_height
            
        current_floor = min((current_height // HEIGHT) + 1, TOTAL_FLOORS)
        # トラップで戻された時用に、現在高さがマイナスにならないよう調整
        display_floor = max(1, current_floor)

        # --- 描画処理 ---
        screen.fill(BLACK)

        # ゴールの描画
        goal_rect = goal_block.get_rect()
        goal_draw_y = goal_rect.y - camera_y
        if -100 < goal_draw_y < HEIGHT + 100:
            screen.blit(goal_block.get_image(), (goal_rect.x, goal_draw_y))

        # 足場の描画
        for plat in platforms:
            plat_rect = plat.get_rect()
            draw_y = plat_rect.y - camera_y
            if -50 < draw_y < HEIGHT + 50:
                screen.blit(plat.get_image(), (plat_rect.x, draw_y))

        # プレイヤーの描画
        player_draw_y = p_rect.y - camera_y
        screen.blit(player.get_image(), (p_rect.x, player_draw_y))

        # チャージゲージと方向指示器
        if player.get_is_charging() and not player.get_is_clear():
            gauge_width = (player.get_charge_power() / player.get_max_charge()) * 40
            pygame.draw.rect(screen, COLOR_RED_UI, (p_rect.centerx - 20, player_draw_y - 15, gauge_width, 8))
        
        arrow_x = p_rect.right + 5 if player.get_direction() == 1 else p_rect.left - 10
        pygame.draw.rect(screen, WHITE, (arrow_x, player_draw_y + 15, 5, 5))

        # 情報表示
        ui_text = font.render(f"Floor: {display_floor} / {TOTAL_FLOORS}   Max: {max_height // 10}m", True, WHITE)
        screen.blit(ui_text, (10, 10))

        # ゴール演出
        if player.get_is_clear():
            clear_text = large_font.render("CLEAR!!", True, GOLD)
            text_rect = clear_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            screen.blit(clear_text, text_rect)
            
            sub_text = font.render("CONGRATULATIONS!", True, WHITE)
            sub_rect = sub_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            screen.blit(sub_text, sub_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()