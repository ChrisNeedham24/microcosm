from typing import List, Optional, Tuple

from source.foundation.models import Settlement, Player, Improvement, Unit, Blessing, CompletedConstruction, UnitPlan, \
    Heathen, AttackData, SetlAttackData, Victory, InvestigationResult, OverlayType, SettlementAttackType, PauseOption, \
    Project, ConstructionMenu, HealData, Achievement, StandardOverlayView, GameConfig


class Overlay:
    """
    The class responsible for keeping track of the overlay menus in-game.
    """

    def __init__(self, cfg: GameConfig):
        """
        Initialise the many variables used by the overlay to keep track of game state.
        :param cfg: The configuration for the current game.
        """
        self.showing: List[OverlayType] = []  # What the overlay is currently displaying.
        self.current_settlement: Optional[Settlement] = None
        self.current_player: Optional[Player] = None  # Will always be the non-AI player on this machine.
        self.available_constructions: List[Improvement] = []
        self.available_projects: List[Project] = []
        self.available_unit_plans: List[UnitPlan] = []
        self.selected_construction: Optional[Improvement | Project | UnitPlan] = None
        # These boundaries are used to keep track of which improvements/units/blessings are currently displayed. This is
        # for scrolling functionality to work.
        self.construction_boundaries: Tuple[int, int] = 0, 5
        self.unit_plan_boundaries: Tuple[int, int] = 0, 5
        self.current_construction_menu: ConstructionMenu = ConstructionMenu.IMPROVEMENTS
        self.selected_unit: Optional[Unit | Heathen] = None
        self.available_blessings: List[Blessing] = []
        self.selected_blessing: Optional[Blessing] = None
        self.blessing_boundaries: Tuple[int, int] = 0, 5
        self.problematic_settlements: List[Settlement] = []  # Settlements with no construction.
        self.has_no_blessing: bool = False  # Whether the player is not undergoing a blessing currently.
        self.will_have_negative_wealth = False  # If the player will go into negative wealth if they end their turn.
        # Any blessings or constructions that have just completed, or any settlements that have levelled up.
        self.completed_blessing: Optional[Blessing] = None
        self.completed_constructions: List[CompletedConstruction] = []
        self.levelled_up_settlements: List[Settlement] = []
        # Data to display from attacks or healing actions.
        self.attack_data: Optional[AttackData] = None
        self.heal_data: Optional[HealData] = None
        self.setl_attack_data: Optional[SetlAttackData] = None
        # The option that the player has selected when attacking a settlement.
        self.setl_attack_opt: Optional[SettlementAttackType] = None
        self.attacked_settlement: Optional[Settlement] = None
        self.attacked_settlement_owner: Optional[Player] = None
        self.sieged_settlement: Optional[Settlement] = None
        self.sieger_of_settlement: Optional[Player] = None
        self.pause_option: PauseOption = PauseOption.RESUME
        self.has_saved: bool = False
        self.current_victory: Optional[Victory] = None  # Victory data, if one has been achieved.
        self.just_eliminated: Optional[Player] = None
        self.close_to_vics: List[Victory] = []
        self.investigation_result: Optional[InvestigationResult] = None
        self.night_beginning: bool = False
        self.settlement_status_boundaries: Tuple[int, int] = 0, 9
        self.show_auto_construction_prompt: bool = False
        self.show_additional_controls: bool = False
        self.show_unit_passengers: bool = False
        self.unit_passengers_idx: int = 0
        self.new_achievements: List[Achievement] = []
        self.current_standard_overlay_view: StandardOverlayView = StandardOverlayView.BLESSINGS
        self.current_game_config: GameConfig = cfg
        self.total_settlement_count: int = 0
        self.player_changing: Optional[Player] = None
        self.changed_player_is_leaving: Optional[bool] = None  # False means they're joining.

    """
    Note that the below methods feature some somewhat complex conditional logic in terms of which overlays may be
    displayed along with which other overlays.
    """

    def toggle_standard(self):
        """
        Toggle the standard overlay.
        """
        # Ensure that we can only remove the standard overlay if the player is not choosing a blessing.
        if OverlayType.STANDARD in self.showing and not self.is_blessing():
            self.showing.remove(OverlayType.STANDARD)
        elif not self.is_tutorial() and not self.is_lvl_notif() and not self.is_constr_notif() and \
                not self.is_bless_notif() and not self.is_deployment() and not self.is_warning() and \
                not self.is_pause() and not self.is_controls() and not self.is_victory() and \
                not self.is_constructing() and not self.is_ach_notif():
            self.showing.append(OverlayType.STANDARD)

    def navigate_standard(self, up: bool = False, down: bool = False, left: bool = False, right: bool = False):
        """
        Navigate the standard overlay.
        :param up: Whether the up arrow key was pressed.
        :param down: Whether the down arrow key was pressed.
        :param left: Whether the left arrow key was pressed.
        :param right: Whether the right arrow key was pressed.
        """
        if left:
            match self.current_standard_overlay_view:
                case StandardOverlayView.VAULT:
                    self.current_standard_overlay_view = StandardOverlayView.BLESSINGS
                case StandardOverlayView.SETTLEMENTS:
                    self.current_standard_overlay_view = StandardOverlayView.VAULT
                case StandardOverlayView.VICTORIES:
                    self.current_standard_overlay_view = StandardOverlayView.SETTLEMENTS
        elif right:
            match self.current_standard_overlay_view:
                case StandardOverlayView.BLESSINGS:
                    self.current_standard_overlay_view = StandardOverlayView.VAULT
                case StandardOverlayView.VAULT:
                    self.current_standard_overlay_view = StandardOverlayView.SETTLEMENTS
                case StandardOverlayView.SETTLEMENTS:
                    self.current_standard_overlay_view = StandardOverlayView.VICTORIES
        # Only allow navigation if the player has enough settlements to warrant scrolling.
        elif self.current_standard_overlay_view is StandardOverlayView.SETTLEMENTS and \
                len(self.current_player.settlements) > 9:
            if down and self.settlement_status_boundaries[1] != len(self.current_player.settlements):
                self.settlement_status_boundaries = \
                    self.settlement_status_boundaries[0] + 1, self.settlement_status_boundaries[1] + 1
            elif up and self.settlement_status_boundaries[0] != 0:
                self.settlement_status_boundaries = \
                    self.settlement_status_boundaries[0] - 1, self.settlement_status_boundaries[1] - 1

    def toggle_construction(self,
                            available_constructions: List[Improvement],
                            available_projects: List[Project],
                            available_unit_plans: List[UnitPlan]):
        """
        Toggle the construction overlay.
        :param available_constructions: The available improvements that the player can select from.
        :param available_projects: The available projects that the player can select from.
        :param available_unit_plans: The available units that the player may recruit from.
        """
        if OverlayType.CONSTRUCTION in self.showing:
            self.showing.remove(OverlayType.CONSTRUCTION)
        elif not self.is_standard() and not self.is_blessing() and not self.is_lvl_notif() and \
                not self.is_constr_notif() and not self.is_bless_notif() and not self.is_warning() and \
                not self.is_deployment() and not self.is_pause() and not self.is_controls() and \
                not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.CONSTRUCTION)
            self.available_constructions = available_constructions
            self.available_projects = available_projects
            self.available_unit_plans = available_unit_plans
            if len(available_constructions) > 0:
                self.current_construction_menu = ConstructionMenu.IMPROVEMENTS
                self.selected_construction = self.available_constructions[0]
                self.construction_boundaries = 0, 5
            # If there are no available improvements, display the projects instead.
            else:
                self.current_construction_menu = ConstructionMenu.PROJECTS
                self.selected_construction = self.available_projects[0]

    def navigate_constructions(self, down: bool):
        """
        Navigate the constructions overlay.
        :param down: Whether the down arrow key was pressed. If this is false, the up arrow key was pressed.
        """
        list_to_use: list
        match self.current_construction_menu:
            case ConstructionMenu.IMPROVEMENTS:
                list_to_use = self.available_constructions
            case ConstructionMenu.PROJECTS:
                list_to_use = self.available_projects
            case _:
                list_to_use = self.available_unit_plans

        # Scroll up/down the improvements/units list, ensuring not to exceed the bounds in either direction.
        if down and self.selected_construction is not None:
            current_index = list_to_use.index(self.selected_construction)
            if current_index != len(list_to_use) - 1:
                self.selected_construction = list_to_use[current_index + 1]
                if self.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                    if current_index == self.construction_boundaries[1]:
                        self.construction_boundaries = \
                            self.construction_boundaries[0] + 1, self.construction_boundaries[1] + 1
                elif self.current_construction_menu is ConstructionMenu.UNITS:
                    if current_index == self.unit_plan_boundaries[1]:
                        self.unit_plan_boundaries = \
                            self.unit_plan_boundaries[0] + 1, self.unit_plan_boundaries[1] + 1
            else:
                self.selected_construction = None
        elif not down:
            if self.selected_construction is None:
                self.selected_construction = list_to_use[len(list_to_use) - 1]
            else:
                current_index = list_to_use.index(self.selected_construction)
                if current_index != 0:
                    self.selected_construction = list_to_use[current_index - 1]
                    if self.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                        if current_index == self.construction_boundaries[0]:
                            self.construction_boundaries = \
                                self.construction_boundaries[0] - 1, self.construction_boundaries[1] - 1
                    elif self.current_construction_menu is ConstructionMenu.UNITS:
                        if current_index == self.unit_plan_boundaries[0]:
                            self.unit_plan_boundaries = \
                                self.unit_plan_boundaries[0] - 1, self.unit_plan_boundaries[1] - 1

    def is_constructing(self) -> bool:
        """
        Returns whether the construction overlay is currently being displayed.
        :return: Whether the construction overlay is being displayed.
        """
        return OverlayType.CONSTRUCTION in self.showing

    def toggle_blessing(self, available_blessings: List[Blessing]):
        """
        Toggle the blessings overlay.
        :param available_blessings: The available blessings for the player to select from.
        """
        if OverlayType.BLESSING in self.showing:
            self.showing.remove(OverlayType.BLESSING)
        elif not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_bless_notif() and \
                not self.is_deployment() and not self.is_warning() and not self.is_pause() and \
                not self.is_controls() and not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.BLESSING)
            self.available_blessings = available_blessings
            self.selected_blessing = self.available_blessings[0]
            self.blessing_boundaries = 0, 5

    def navigate_blessings(self, down: bool):
        """
        Navigate the blessings overlay.
        :param down: Whether the down arrow key was pressed. If this is false, the up arrow key was pressed.
        """
        # Scroll up/down the blessings list, ensuring not to exceed the bounds in either direction.
        if down and self.selected_blessing is not None:
            current_index = self.available_blessings.index(self.selected_blessing)
            if current_index != len(self.available_blessings) - 1:
                self.selected_blessing = self.available_blessings[current_index + 1]
                if current_index == self.blessing_boundaries[1]:
                    self.blessing_boundaries = self.blessing_boundaries[0] + 1, self.blessing_boundaries[1] + 1
            else:
                self.selected_blessing = None
        elif not down:
            if self.selected_blessing is None:
                self.selected_blessing = self.available_blessings[len(self.available_blessings) - 1]
            else:
                current_index = self.available_blessings.index(self.selected_blessing)
                if current_index != 0:
                    self.selected_blessing = self.available_blessings[current_index - 1]
                    if current_index == self.blessing_boundaries[0]:
                        self.blessing_boundaries = self.blessing_boundaries[0] - 1, self.blessing_boundaries[1] - 1

    def is_standard(self) -> bool:
        """
        Returns whether the standard overlay is currently being displayed.
        :return: Whether the standard overlay is being displayed.
        """
        return OverlayType.STANDARD in self.showing

    def is_blessing(self) -> bool:
        """
        Returns whether the blessings overlay is currently being displayed.
        :return: Whether the blessings overlay is being displayed.
        """
        return OverlayType.BLESSING in self.showing

    def toggle_settlement(self, settlement: Optional[Settlement], player: Player):
        """
        Toggle the settlement overlay.
        :param settlement: The selected settlement to display.
        :param player: The current player. Will always be the non-AI player on this machine.
        """
        # Ensure that we can only remove the settlement overlay if the player is not choosing a construction.
        if OverlayType.SETTLEMENT in self.showing and not self.is_constructing():
            self.showing.remove(OverlayType.SETTLEMENT)
        elif not self.is_unit() and not self.is_standard() and not self.is_setl_click() and not self.is_blessing() and \
                not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_deployment() and \
                not self.is_warning() and not self.is_bless_notif() and not self.is_pause() and \
                not self.is_controls() and not self.is_victory() and not self.is_investigation() and \
                not self.is_ach_notif():
            self.showing.append(OverlayType.SETTLEMENT)
            self.current_settlement = settlement
            self.current_player = player

    def update_settlement(self, settlement: Settlement):
        """
        Updates the currently-displayed settlement in the settlement overlay. Used in cases where the player is
        iterating through their settlements with the TAB key.
        :param settlement: The new settlement to display.
        """
        self.current_settlement = settlement

    def update_unit(self, unit: Unit):
        """
        Updates the currently-displayed unit in the unit overlay. Used in cases where the player is iterating through
        their units with the SPACE key.
        :param unit: The new unit to display.
        """
        self.selected_unit = unit

    def toggle_deployment(self):
        """
        Toggle the deployment overlay.
        """
        if OverlayType.DEPLOYMENT in self.showing:
            self.showing.remove(OverlayType.DEPLOYMENT)
        elif not self.is_warning() and not self.is_bless_notif() and not self.is_constr_notif() and \
                not self.is_lvl_notif() and not self.is_pause() and not self.is_controls() and \
                not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.DEPLOYMENT)

    def is_deployment(self):
        """
        Returns whether the deployment overlay is currently being displayed.
        :return: Whether the deployment overlay is being displayed.
        """
        return OverlayType.DEPLOYMENT in self.showing

    def toggle_unit(self, unit: Optional[Unit | Heathen]):
        """
        Toggle the unit overlay.
        :param unit: The currently-selected unit to display in the overlay.
        """
        if OverlayType.UNIT in self.showing and not self.is_setl_click() and not self.is_investigation():
            self.showing.remove(OverlayType.UNIT)
        elif not self.is_setl() and not self.is_standard() and not self.is_setl_click() and not self.is_blessing() and \
                not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_deployment() and \
                not self.is_warning() and not self.is_bless_notif() and not self.is_pause() and \
                not self.is_controls() and not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.UNIT)
            self.selected_unit = unit

    def toggle_tutorial(self):
        """
        Toggle the tutorial overlay.
        """
        if OverlayType.TUTORIAL in self.showing:
            self.showing.remove(OverlayType.TUTORIAL)
        else:
            self.showing.append(OverlayType.TUTORIAL)

    def is_tutorial(self) -> bool:
        """
        Returns whether the tutorial overlay is currently being displayed.
        :return: Whether the tutorial overlay is being displayed.
        """
        return OverlayType.TUTORIAL in self.showing

    def is_unit(self):
        """
        Returns whether the unit overlay is currently being displayed.
        :return: Whether the unit overlay is being displayed.
        """
        return OverlayType.UNIT in self.showing

    def navigate_unit(self, down: bool):
        """
        Navigate the passengers part of the unit overlay for deployer units.
        :param down: Whether the down arrow key was pressed. If this is false, the up arrow key was pressed.
        """
        if down and self.unit_passengers_idx + 1 < len(self.selected_unit.passengers):
            self.unit_passengers_idx += 1
        elif not down and self.unit_passengers_idx - 1 >= 0:
            self.unit_passengers_idx -= 1

    def can_iter_settlements_units(self) -> bool:
        """
        Returns whether the player can iterate through either their settlements or units.
        :return: Whether player settlement/unit iteration is permitted.
        """
        return not self.is_victory() and not self.is_controls() and not self.is_pause() and \
            not self.is_deployment() and not self.is_warning() and not self.is_bless_notif() and \
            not self.is_constr_notif() and not self.is_lvl_notif() and not self.is_blessing() and \
            not self.is_standard() and not self.is_constructing() and not self.is_setl_click() and \
            not self.is_investigation() and not self.is_ach_notif()

    def can_jump_to_setl(self) -> bool:
        """
        Returns whether the player can jump to an idle settlement.
        :return: Whether jumping to an idle settlement is permitted.
        """
        return not self.is_victory() and not self.is_controls() and not self.is_pause() and \
            not self.is_deployment() and not self.is_bless_notif() and not self.is_constr_notif() and \
            not self.is_lvl_notif() and not self.is_blessing() and not self.is_constructing() and \
            not self.is_setl_click() and not self.is_investigation() and not self.is_ach_notif()

    def is_setl(self):
        """
        Returns whether the settlement overlay is currently being displayed.
        :return: Whether the settlement overlay is being displayed.
        """
        return OverlayType.SETTLEMENT in self.showing

    def toggle_warning(self, settlements: List[Settlement], no_blessing: bool, will_have_negative_wealth: bool):
        """
        Toggle the warning overlay.
        :param settlements: The player settlements that have no construction.
        :param no_blessing: Whether the player is currently not undergoing a blessing.
        :param will_have_negative_wealth: Whether the player will have negative wealth next turn.
        """
        if OverlayType.WARNING in self.showing:
            self.showing.remove(OverlayType.WARNING)
        else:
            self.showing.append(OverlayType.WARNING)
            self.problematic_settlements = settlements
            self.has_no_blessing = no_blessing
            self.will_have_negative_wealth = will_have_negative_wealth

    def is_warning(self):
        """
        Returns whether the warning overlay is currently being displayed.
        :return: Whether the warning overlay is being displayed.
        """
        return OverlayType.WARNING in self.showing

    def remove_warning_if_possible(self):
        """
        If the warning overlay is currently being displayed, remove it. Used for cases in which the warning overlay is
        displayed and any user interaction with the mouse or keyboard should remove it.
        """
        if OverlayType.WARNING in self.showing:
            self.showing.remove(OverlayType.WARNING)

    def toggle_blessing_notification(self, blessing: Optional[Blessing]):
        """
        Toggle the blessing notification overlay.
        :param blessing: The blessing completed by the player.
        """
        if OverlayType.BLESS_NOTIF in self.showing:
            self.showing.remove(OverlayType.BLESS_NOTIF)
        else:
            self.showing.append(OverlayType.BLESS_NOTIF)
            self.completed_blessing = blessing

    def is_bless_notif(self):
        """
        Returns whether the blessing notification overlay is currently being displayed.
        :return: Whether the blessing notification overlay is being displayed.
        """
        return OverlayType.BLESS_NOTIF in self.showing

    def toggle_construction_notification(self, constructions: List[CompletedConstruction]):
        """
        Toggle the construction notification overlay.
        :param constructions: The list of constructions that were completed in the last turn.
        """
        if OverlayType.CONSTR_NOTIF in self.showing:
            self.showing.remove(OverlayType.CONSTR_NOTIF)
        else:
            self.showing.append(OverlayType.CONSTR_NOTIF)
            self.completed_constructions = constructions

    def is_constr_notif(self):
        """
        Returns whether the construction notification overlay is currently being displayed.
        :return: Whether the construction notification overlay is being displayed.
        """
        return OverlayType.CONSTR_NOTIF in self.showing

    def toggle_level_up_notification(self, settlements: List[Settlement]):
        """
        Toggle the level up notification overlay.
        :param settlements: The list of settlements that levelled up in the last turn.
        """
        if OverlayType.LEVEL_NOTIF in self.showing:
            self.showing.remove(OverlayType.LEVEL_NOTIF)
        else:
            self.showing.append(OverlayType.LEVEL_NOTIF)
            self.levelled_up_settlements = settlements

    def is_lvl_notif(self):
        """
        Returns whether the level up notification overlay is currently being displayed.
        :return: Whether the level up notification overlay is being displayed.
        """
        return OverlayType.LEVEL_NOTIF in self.showing

    def toggle_attack(self, attack_data: Optional[AttackData]):
        """
        Toggle the attack overlay.
        :param attack_data: The data for the overlay to display.
        """
        if OverlayType.ATTACK in self.showing:
            # We need this if-else in order to update attacks if they occur multiple times within the window.
            if attack_data is None:
                self.showing.remove(OverlayType.ATTACK)
            else:
                self.attack_data = attack_data
        else:
            self.showing.append(OverlayType.ATTACK)
            self.attack_data = attack_data

    def is_attack(self):
        """
        Returns whether the attack overlay is currently being displayed.
        :return: Whether the attack overlay is being displayed.
        """
        return OverlayType.ATTACK in self.showing

    def toggle_heal(self, heal_data: Optional[HealData]):
        """
        Toggle the heal overlay.
        :param heal_data: The data for the overlay to display.
        """
        if OverlayType.HEAL in self.showing:
            # We need this if-else in order to update healing actions if they occur multiple times within the window.
            if heal_data is None:
                self.showing.remove(OverlayType.HEAL)
            else:
                self.heal_data = heal_data
        else:
            self.showing.append(OverlayType.HEAL)
            self.heal_data = heal_data

    def is_heal(self):
        """
        Returns whether the heal overlay is currently being displayed.
        :return: Whether the heal overlay is currently being displayed.
        """
        return OverlayType.HEAL in self.showing

    def toggle_setl_attack(self, attack_data: Optional[SetlAttackData]):
        """
        Toggle the settlement attack overlay.
        :param attack_data: The data for the overlay to display.
        """
        if OverlayType.SETL_ATTACK in self.showing:
            # We need this if-else in order to update attacks if they occur multiple times within the window.
            if attack_data is None:
                self.showing.remove(OverlayType.SETL_ATTACK)
            else:
                self.setl_attack_data = attack_data
        else:
            self.showing.append(OverlayType.SETL_ATTACK)
            self.setl_attack_data = attack_data

    def is_setl_attack(self):
        """
        Returns whether the settlement attack overlay is currently being displayed.
        :return: Whether the settlement attack overlay is being displayed.
        """
        return OverlayType.SETL_ATTACK in self.showing

    def toggle_siege_notif(self, sieged: Optional[Settlement], sieger: Optional[Player]):
        """
        Toggle the siege notification overlay.
        :param sieged: The settlement being placed under siege.
        :param sieger: The player placing the settlement under siege.
        """
        if OverlayType.SIEGE_NOTIF in self.showing:
            self.showing.remove(OverlayType.SIEGE_NOTIF)
        else:
            self.showing.append(OverlayType.SIEGE_NOTIF)
            self.sieged_settlement = sieged
            self.sieger_of_settlement = sieger

    def is_siege_notif(self):
        """
        Returns whether the siege notification overlay is currently being displayed.
        :return: Whether the siege notification overlay is currently being displayed.
        """
        return OverlayType.SIEGE_NOTIF in self.showing

    def toggle_victory(self, victory: Victory):
        """
        Toggle the victory overlay.
        :param victory: The victory achieved by a player.
        """
        self.showing.append(OverlayType.VICTORY)
        self.current_victory = victory

    def is_victory(self):
        """
        Returns whether the victory overlay is currently being displayed.
        :return: Whether the victory overlay is being displayed.
        """
        return OverlayType.VICTORY in self.showing

    def toggle_setl_click(self, att_setl: Optional[Settlement], owner: Optional[Player]):
        """
        Toggle the settlement click overlay.
        :param att_setl: The settlement clicked on by the player.
        :param owner: The owner of the clicked-on settlement.
        """
        if OverlayType.SETL_CLICK in self.showing:
            self.showing.remove(OverlayType.SETL_CLICK)
        elif not self.is_standard() and not self.is_constructing() and not self.is_blessing() and \
                not self.is_deployment() and not self.is_tutorial() and not self.is_warning() and \
                not self.is_bless_notif() and not self.is_constr_notif() and not self.is_lvl_notif() and \
                not self.is_pause() and not self.is_controls() and not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.SETL_CLICK)
            self.setl_attack_opt = SettlementAttackType.ATTACK
            self.attacked_settlement = att_setl
            self.attacked_settlement_owner = owner

    def navigate_setl_click(self, left: bool = False, right: bool = False, up: bool = False, down: bool = False):
        """
        Navigate the settlement click overlay.
        :param left: Whether the left arrow key was pressed.
        :param right: Whether the right arrow key was pressed.
        :param up: Whether the up arrow key was pressed.
        :param down: Whether the down arrow key was pressed.
        """
        if down:
            self.setl_attack_opt = None
        # From cancel, the up key will take you to the left option.
        elif up or left:
            self.setl_attack_opt = SettlementAttackType.ATTACK
        elif right:
            self.setl_attack_opt = SettlementAttackType.BESIEGE

    def is_setl_click(self) -> bool:
        """
        Returns whether the settlement click overlay is currently being displayed.
        :return: Whether the settlement click overlay is being displayed.
        """
        return OverlayType.SETL_CLICK in self.showing

    def toggle_pause(self):
        """
        Toggle the pause overlay.
        """
        # Ensure that we can only remove the pause overlay if the player is not viewing the controls.
        if OverlayType.PAUSE in self.showing and not self.is_controls():
            self.showing.remove(OverlayType.PAUSE)
        elif not self.is_victory() and not self.is_tutorial():
            self.showing.append(OverlayType.PAUSE)
            self.pause_option = PauseOption.RESUME
            self.has_saved = False

    def navigate_pause(self, down: bool):
        """
        Navigate the pause overlay.
        :param down: Whether the down arrow key was pressed. If this is false, the up arrow key was pressed.
        """
        if down:
            match self.pause_option:
                case PauseOption.RESUME:
                    self.pause_option = PauseOption.SAVE
                    self.has_saved = False
                case PauseOption.SAVE:
                    self.pause_option = PauseOption.CONTROLS
                case PauseOption.CONTROLS:
                    self.pause_option = PauseOption.QUIT
        else:
            match self.pause_option:
                case PauseOption.SAVE:
                    self.pause_option = PauseOption.RESUME
                case PauseOption.CONTROLS:
                    self.pause_option = PauseOption.SAVE
                    self.has_saved = False
                case PauseOption.QUIT:
                    self.pause_option = PauseOption.CONTROLS

    def is_pause(self) -> bool:
        """
        Returns whether the pause overlay is currently being displayed.
        :return: Whether the pause overlay is being displayed.
        """
        return OverlayType.PAUSE in self.showing

    def toggle_controls(self):
        """
        Toggle the controls overlay.
        """
        if OverlayType.CONTROLS in self.showing:
            self.showing.remove(OverlayType.CONTROLS)
        elif not self.is_victory():
            self.showing.append(OverlayType.CONTROLS)

    def is_controls(self) -> bool:
        """
        Returns whether the controls overlay is currently being displayed.
        :return: Whether the controls overlay is being displayed.
        """
        return OverlayType.CONTROLS in self.showing

    def toggle_elimination(self, eliminated: Optional[Player]):
        """
        Toggle the elimination overlay.
        :param eliminated: The player that has just been eliminated.
        """
        if OverlayType.ELIMINATION in self.showing:
            self.showing.remove(OverlayType.ELIMINATION)
        else:
            self.showing.append(OverlayType.ELIMINATION)
            self.just_eliminated = eliminated

    def is_elimination(self) -> bool:
        """
        Returns whether the elimination overlay is currently being displayed.
        :return: Whether the elimination overlay is being displayed.
        """
        return OverlayType.ELIMINATION in self.showing

    def toggle_close_to_vic(self, close_to_vics: List[Victory]):
        """
        Toggle the close-to-victory overlay.
        :param close_to_vics: The victories that are close to being achieved, and the players close to achieving them.
        """
        if OverlayType.CLOSE_TO_VIC in self.showing:
            self.showing.remove(OverlayType.CLOSE_TO_VIC)
        else:
            self.showing.append(OverlayType.CLOSE_TO_VIC)
            self.close_to_vics = close_to_vics

    def is_close_to_vic(self) -> bool:
        """
        Returns whether the close-to-victory overlay is currently being displayed.
        :return: Whether the close-to-victory overlay is being displayed.
        """
        return OverlayType.CLOSE_TO_VIC in self.showing

    def toggle_investigation(self, inv_res: Optional[InvestigationResult]):
        """
        Toggle the investigation overlay.
        :param inv_res: The result of a just-executed investigation on a relic.
        """
        if OverlayType.INVESTIGATION in self.showing:
            self.showing.remove(OverlayType.INVESTIGATION)
        elif not self.is_standard() and not self.is_constructing() and not self.is_blessing() and \
                not self.is_deployment() and not self.is_tutorial() and not self.is_warning() and \
                not self.is_bless_notif() and not self.is_constr_notif() and not self.is_lvl_notif() and \
                not self.is_pause() and not self.is_controls() and not self.is_victory() and not self.is_ach_notif():
            self.showing.append(OverlayType.INVESTIGATION)
            self.investigation_result = inv_res

    def is_investigation(self) -> bool:
        """
        Returns whether the investigation overlay is currently being displayed.
        :return: Whether the investigation overlay is being displayed.
        """
        return OverlayType.INVESTIGATION in self.showing

    def toggle_night(self, beginning: Optional[bool]):
        """
        Toggle the night overlay.
        :param beginning: Whether the night is beginning (will be False if dawn has broken).
        """
        if OverlayType.NIGHT in self.showing:
            self.showing.remove(OverlayType.NIGHT)
        else:
            self.showing.append(OverlayType.NIGHT)
            self.night_beginning = beginning

    def is_night(self) -> bool:
        """
        Returns whether the night overlay is currently being displayed.
        :return: Whether the night overlay is being displayed.
        """
        return OverlayType.NIGHT in self.showing

    def toggle_ach_notif(self, new_achievements: List[Achievement]):
        """
        Toggle the achievement notification overlay.
        :param new_achievements: Any new achievements to notify the player of.
        """
        if OverlayType.ACH_NOTIF in self.showing:
            # If the player obtains multiple achievements in the course of the same turn, we want to display them
            # individually. As such, when toggling the overlay off, only actually remove the overlay if this is the last
            # achievement to display.
            self.new_achievements.pop()
            if not self.new_achievements:
                self.showing.remove(OverlayType.ACH_NOTIF)
        else:
            self.showing.append(OverlayType.ACH_NOTIF)
            self.new_achievements = new_achievements

    def is_ach_notif(self):
        """
        Returns whether the achievement notification overlay is currently being displayed.
        :return: Whether the achievement notification overlay is being displayed.
        """
        return OverlayType.ACH_NOTIF in self.showing

    def toggle_player_change(self,
                             player_changing: Optional[Player],
                             changed_player_is_leaving: Optional[bool]):
        """
        Toggle the player change overlay.
        :param player_changing: The player either leaving or joining the game.
        :param changed_player_is_leaving: Whether the player is leaving.
        """
        if OverlayType.PLAYER_CHANGE in self.showing:
            self.showing.remove(OverlayType.PLAYER_CHANGE)
        else:
            self.showing.append(OverlayType.PLAYER_CHANGE)
            self.player_changing = player_changing
            self.changed_player_is_leaving = changed_player_is_leaving

    def is_player_change(self):
        """
        Returns whether the player change overlay is currently being displayed.
        :return: Whether the player change overlay is currently being displayed.
        """
        return OverlayType.PLAYER_CHANGE in self.showing

    def toggle_desync(self):
        """
        Toggle the desync overlay.
        """
        self.showing.append(OverlayType.DESYNC)

    def is_desync(self):
        """
        Returns whether the desync overlay is currently being displayed.
        :return: Whether the desync overlay is being displayed.
        """
        return OverlayType.DESYNC in self.showing

    def remove_layer(self) -> Optional[OverlayType]:
        """
        Remove a layer of the overlay, where possible.
        :return: An OverlayType, if the given type requires further action. More specifically, when toggling the unit
        and settlement overlays, action is also required to reset the selected unit/settlement.
        """
        if self.is_ach_notif():
            self.toggle_ach_notif([])
        elif self.is_night():
            self.toggle_night(None)
        elif self.is_close_to_vic():
            self.toggle_close_to_vic([])
        elif self.is_bless_notif():
            self.toggle_blessing_notification(None)
        elif self.is_constr_notif():
            self.toggle_construction_notification([])
        elif self.is_lvl_notif():
            self.toggle_level_up_notification([])
        elif self.is_warning():
            self.remove_warning_if_possible()
        elif self.is_investigation():
            self.toggle_investigation(None)
        elif self.is_controls():
            self.toggle_controls()
        elif self.is_pause():
            self.toggle_pause()
        elif self.is_blessing():
            self.toggle_blessing([])
        elif self.is_setl_click():
            self.toggle_setl_click(None, None)
        elif self.is_standard():
            self.toggle_standard()
        elif self.is_constructing():
            self.toggle_construction([], [], [])
        elif self.is_unit():
            self.toggle_unit(None)
            return OverlayType.UNIT
        elif self.is_setl():
            self.toggle_settlement(None, self.current_player)
            return OverlayType.SETTLEMENT
        return None
