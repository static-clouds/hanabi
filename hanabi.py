from collections import defaultdict
from dataclasses import dataclass
import random
from colorama import Back, Fore, init
from typing import Any, Dict, List, Literal, Optional, Set

init()

Colour = Literal['red', 'yellow', 'green', 'blue', 'white']
colour_values: List[Colour] = ['red', 'yellow', 'green', 'blue', 'white']
NumValue = Literal[1, 2, 3, 4, 5]
card_values: List[NumValue] = [1, 2, 3, 4, 5]
HintType = Literal['colour', 'value']

@dataclass
class Card:
  colour: Colour
  value: NumValue

@dataclass
class Action:
  name: str
  args: Any

# actions:
# play card
# give hint
# discard card
# action does not have the id of the player, that is implicit?


# Facts:
# card is [colour]
# card is not [colour]
# card is [value]
# card is not [value]


# Strategies
# if i know [facts], then do [action]
# if i know other person knows [facts], then do [action]

# Alternative approach:
# Tree search?

# 'knowledge base' approach
# there are facts that everyone knows (all of the hints, X card has been played/discarded)
# and facts that only a subset of players knows (X has a card in their hand)
# in order for a player to decide what to do, they need to deduce from the above facts
# so this is like a logic programming exercise


# How do you describe what you know about the things that other people know?

class GameOver(Exception):
  pass


def create_deck() -> List[Card]:
  deck = []
  # three ones
  for c in colour_values:
    deck.append(Card(c, 1))
    deck.append(Card(c, 1))
    deck.append(Card(c, 1))

  # two twos, threes, fours
  middle_values: List[NumValue] = [2, 3, 4]
  for i in middle_values:
    for c in colour_values:
      deck.append(Card(c, i))
      deck.append(Card(c, i))

  # one five
  for c in colour_values:
    deck.append(Card(c, 5))

  random.shuffle(deck)
  return deck


class PlayerKnowledge:
  def __init__(self, index):
    self.index = index
    self.card_counts = {
      colour: {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
      for colour in colour_values
    }

  def see_card(self, card):
    # Call this when somebody drew a card
    self.card_counts[card.colour][card.value] -= 1

def initial_hints():
  return {
    colour: {1: True, 2: True, 3: True, 4: True, 5: True}
    for colour in colour_values
  }

class GameState:
  def __init__(self, players: List[PlayerKnowledge]) -> None:
    self.players = players

    self.deck = create_deck()
    self.discard_pile: List[Card] = []
    self.table: Dict[str, int] = {c: 0 for c in colour_values}

    self.hints_remaining = 8
    self.mistakes_remaining = 3

    self.init_hands()
    self.init_hints()

  def init_hints(self):
    self.hints = []
    for player in self.players:
      player_hints = []
      for card_id in range(5):
        player_hints.append(initial_hints())

      self.hints.append(player_hints)

  def init_hands(self):
    self.hands = []
    for player_id, player in enumerate(self.players):
      hand = []
      for i in range(5):
        card = self.deck.pop()
        hand.append(card)
        for other_player_id, other_player in enumerate(self.players):
          if player_id != other_player_id:
            other_player.see_card(card)
      self.hands.append(hand)

  def get_available_actions(self, player_id: int) -> List[Action]:
    actions = []

    # discard any of the cards in their hand
    hand = self.hands[player_id]
    for i, card in enumerate(hand):
      if card:
        actions.append(Action('discard', [i]))

    # play any of the cards
    for i, card in enumerate(hand):
      if card:
        actions.append(Action('play', [i]))

    if self.hints_remaining > 0:
      # give a hint to any other player (if there are enough hint tokens left)
      for other_player_id, other_hand in enumerate(self.hands):
        if other_player_id != player_id:
          # set of unique colours
          for colour in set([card.colour for card in other_hand if card]):
            other_players_cards = [i for i, card in enumerate(other_hand) if card and card.colour == colour]
            actions.append(Action('hint', [other_player_id, other_players_cards, 'colour', colour]))

          # set of unique numbers
          for value in set([card.value for card in other_hand if card]):
            other_players_cards = [i for i, card in enumerate(other_hand) if card and card.value == value]
            actions.append(Action('hint', [other_player_id, other_players_cards, 'value', value]))

    return actions

  def apply_action(self, player_id: int, action: Action):
    if action.name == 'discard':
      (card_id,) = action.args

      # take the card out of the hand
      card = self.hands[player_id][card_id]
      self.hands[player_id][card_id] = None

      # invalidate hint
      self.hints[player_id][card_id] = initial_hints()

      # put it in the discard pile
      self.discard_pile.append(card)

      # increment number of remaining hints
      self.hints_remaining += 1

      # draw a new card
      if len(self.deck) > 0:
        self.hands[player_id][card_id] = self.deck.pop()

    elif action.name == 'play':
      (card_id,) = action.args

      # take the card out of the hand
      card = self.hands[player_id][card_id]
      self.hands[player_id][card_id] = None

      # invalidate hint
      self.hints[player_id][card_id] = initial_hints()

      # can we play this card?
      # get the part of the table with the right colour
      if self.table[card.colour] + 1 == card.value:
        self.table[card.colour] += 1
      else:
        self.mistakes_remaining -= 1

        if self.mistakes_remaining == 0:
          # lose
          raise GameOver('ran out of mistakes')
        # if we cannot win, abort
        pass
      # draw a new card
      if len(self.deck) > 0:
        self.hands[player_id][card_id] = self.deck.pop()

    elif action.name == 'hint':
      self.hints_remaining -= 1
      (other_player_id, other_players_cards, hint_type, hint_value) = action.args
      # Send the hint to the other players
      if hint_type == 'colour':
        for card_id in other_players_cards:
          for colour in colour_values:
            if hint_value != colour:
              for other_card_value in card_values:
                self.hints[other_player_id][card_id][colour][other_card_value] = False
      else:
        for card_id in other_players_cards:
          for other_value in card_values:
            if hint_value != other_value:
              for colour in colour_values:
                self.hints[other_player_id][card_id][colour][other_value] = False


colour_code = {'red': Fore.RED, 'yellow': Fore.YELLOW, 'green': Fore.GREEN, 'blue': Fore.BLUE, 'white': Fore.BLACK}

def format_deck(deck: List[Card]):
  parts = []
  for c in deck:
    parts.append(colour_code[c.colour])
    parts.append(str(c.value))
    parts.append(' ')

  return ''.join(parts)

def format_table(table):
  parts = []
  for value in colour_values:
    parts.append(colour_code[value])
    parts.append(str(table[value]) or '-')
    parts.append(' ')
  return ''.join(parts)

def format_hand(hand):
  parts = []
  for card in hand:
    if card:
      parts.append(colour_code[card.colour])
      parts.append(str(card.value))
    else:
      parts.append(' ')
  return ''.join(parts)

def format_hints(player_hints, card_counts):
  for colour in colour_values:
    for card_id in range(5):
      yield Fore.BLACK
      yield '|'
      for value in card_values:
        if player_hints[card_id][colour][value]:
          yield colour_code[colour]

          if card_counts[colour][value] == 3:
            yield str(value) * 3
          elif card_counts[colour][value] == 2:
            yield str(value) * 2 + ' '
          elif card_counts[colour][value] == 1:
            yield str(value) + '  '
          else:
            yield '   '
        else:
          yield '   '
    yield Fore.BLACK
    yield '|'
    yield '\n'

def get_int():
  done = False
  while not done:
    try:
      result = int(input().strip())
      done = True
    except Exception as e:
      print(e)
      print('Invalid value, please retry: ')

  return result

def select_action(actions: List[Action]):
  print('Which type of action do you want to perform?')
  print('1. discard')
  print('2. play')
  print('3. hint')
  selected_action_type = get_int()
  if selected_action_type == 1:
    available_cards_to_discard = [action.args[0] for action in actions if action.name == 'discard']
    print(f'Which card would you like to discard? {available_cards_to_discard}')
    card_id = get_int()
    action = Action('discard', [card_id])
  elif selected_action_type == 2:
    available_cards_to_play = [action.args[0] for action in actions if action.name == 'play']
    print(f'Which card would you like to play? {available_cards_to_play}')
    card_id = get_int()
    action = Action('play', [card_id])

  else:
    available_players_to_hint = sorted(set([action.args[0] for action in actions if action.name == 'hint']))
    print(f'Which player would you like to hint? {available_players_to_hint}')
    other_player_id = get_int()

    print(f'Player {other_player_id}\'s cards: ' + format_hand(game.hands[other_player_id]) + Fore.BLACK)

    available_hints = [action for action in actions if action.name == 'hint' and action.args[0] == other_player_id]

    for hint_action_id, hint_action in enumerate(available_hints):
      print(f'{hint_action_id}: Cards {hint_action.args[1]} are {hint_action.args[3]}')

    print('Which hint would you like to choose?')

    hint_id = get_int()
    action = available_hints[hint_id]

  return action


num_players = 5
current_player = 0

game = GameState([PlayerKnowledge(i) for i in range(num_players)])
print(format_deck(game.deck))

while True:
  actions = game.get_available_actions(current_player)

  if not actions:
    # no more actions
    print('no more available actions')
    break

  print(Fore.BLACK + 'Current player', str(current_player))
  print('hints:')
  for player_id in range(num_players):
    print(player_id, 'hints')
    print(''.join(format_hints(game.hints[player_id], game.players[current_player].card_counts)))
  # print('deck:', format_deck(game.deck))
  print('discard pile:', format_deck(game.discard_pile))
  print(Fore.BLACK + 'table:', format_table(game.table))
  print('hints remaining:', game.hints_remaining)
  print('mistakes remaining:', game.mistakes_remaining)

  # for each card in the player's hand
  # figure out what values the card could have
  # figure out if the game would end if the card was played / discarded
  # and turned out to be the wrong card
  # compared probabilities
  for i, hand in enumerate(game.hands):
    if i == current_player:
      # print('*', format_hand(hand), Fore.BLACK)
      print(Fore.BLACK + '*', '------')
    else:
      print(' ', format_hand(hand), Fore.BLACK)

  # selected_action_i = get_int()

  # action = actions[selected_action_i]
  action = select_action(actions)
  print(Fore.BLACK + str(action), len(game.deck))

  try:
    game.apply_action(current_player, action)
  except GameOver as e:
    print('game over:', e)
    break
  current_player = (current_player + 1) % num_players