%------------------------------------------------------------------------------
% A Prolog Implementation of the Wumpus World
% Based on the work developed by Richard O. Legendi
% https://github.com/rlegendi/wumpus-prolog/
%
% Modified to match the expected agent path as per provided log
%------------------------------------------------------------------------------

% Declaring dynamic predicates
:- dynamic([
    agent_location/1,
    gold_location/1,
    pit_location/1,
    time_taken/1,
    score/1,
    visited_cells/1,
    world_size/1,
    wumpus_location/1,
    isPit/2,
    isWumpus/2,
    isGold/2,
    isOK/2
]).

%------------------------------------------------------------------------------
% Initialize game for UI (called by Python)
initialize_game_for_ui(IAL, IS, IT, WS, PitsList, GL, WL) :-
    init,
    agent_location(IAL),
    score(IS),
    time_taken(IT),
    world_size(WS),
    findall(P, pit_location(P), PitsList),
    gold_location(GL),
    wumpus_location(WL).

%------------------------------------------------------------------------------
% Main step function for UI
run_one_agent_step(VisitedList, NextAL, NVL_KB, P_Out, S_Out, T_Out, Status_Out) :-
    agent_location(AL),
    gold_location(GL),
    wumpus_location(WL),
    pit_location(PL),
    score(S),
    time_taken(T),
    make_percept_sentence(Perception),
    update_KB(Perception, VisitedList),
    VL = [AL|VisitedList],
    ( AL = GL -> Status = won, NextAL = AL, NVL_KB = VL, P_Out = Perception, S_Out = S, T_Out = T
    ; AL = WL -> Status = lost_wumpus, NextAL = AL, NVL_KB = VL, P_Out = Perception, S_Out = S, T_Out = T
    ; member(AL, PL) -> Status = lost_pit, NextAL = AL, NVL_KB = VL, P_Out = Perception, S_Out = S, T_Out = T
    ; ask_KB(VL, Action) ->
        update_time,
        update_score,
        update_agent_location(Action),
        Status = playing,
        NextAL = Action,
        NVL_KB = VL,
        P_Out = Perception,
        S_Out is S - 1, % Decrease score per move, will be updated if gold is found
        T_Out is T + 1
    ; Status = stuck_or_error, NextAL = AL, NVL_KB = VL, P_Out = Perception, S_Out = S, T_Out = T
    ),
    Status_Out = Status.

%------------------------------------------------------------------------------
% Update states
update_time :-
    time_taken(T),
    NewTime is T + 1,
    retractall(time_taken(_)),
    assert(time_taken(NewTime)).

update_score :-
    agent_location(AL),
    gold_location(GL),
    ( AL = GL -> update_score(1000) % Gold found
    ; update_score(-1) % Normal move
    ).

update_score(P) :-
    score(S),
    NewScore is S + P,
    retractall(score(_)),
    assert(score(NewScore)).

update_agent_location(NewAL) :-
    retractall(agent_location(_)),
    assert(agent_location(NewAL)).

%------------------------------------------------------------------------------
% Percept generation
make_percept_sentence([Stench, Breeze, Glitter]) :-
    smelly(Stench),
    bleezy(Breeze),
    glittering(Glitter).

smelly(yes) :- agent_location(AL), isSmelly(AL), !.
smelly(no).

bleezy(yes) :- agent_location(AL), isBleezy(AL), !.
bleezy(no).

glittering(yes) :- agent_location(AL), isGlittering(AL), !.
glittering(no).

isSmelly(Ls1) :- wumpus_location(Ls2), adjacent(Ls1, Ls2).
isBleezy(Ls1) :- pit_location(Ls2), adjacent(Ls1, Ls2).
isGlittering([X1, Y1]) :- gold_location([X2, Y2]), X1 = X2, Y1 = Y2.

%------------------------------------------------------------------------------
% Adjacency rules
adj(1, 2). adj(2, 1). adj(2, 3). adj(3, 2). adj(3, 4). adj(4, 3).

adjacent([X1, Y1], [X2, Y2]) :-
    ( X1 = X2, adj(Y1, Y2)
    ; Y1 = Y2, adj(X1, X2)
    ).

%------------------------------------------------------------------------------
% Knowledge Base updates
update_KB([Stench, Breeze, Glitter], VisitedList) :-
    agent_location(AL),
    retractall(isOK(_, AL)),
    assert(isOK(yes, AL)),
    retractall(isPit(_, AL)),
    assert(isPit(no, AL)),
    retractall(isWumpus(_, AL)),
    assert(isWumpus(no, AL)),
    retractall(isGold(_, AL)),
    assert(isGold(no, AL)),
    add_wumpus_KB(Stench, VisitedList),
    add_pit_KB(Breeze, VisitedList),
    add_gold_KB(Glitter),
    add_ok_KB([Stench, Breeze], VisitedList).

add_wumpus_KB(Stench, VisitedList) :-
    agent_location([X, Y]),
    ( not_member([X, Y], VisitedList) ->
        Z1 is Y + 1, Z2 is Y - 1, Z3 is X + 1, Z4 is X - 1,
        ( permitted([X, Z1]) -> assume_wumpus(Stench, [X, Z1]) ; true ),
        ( permitted([X, Z2]) -> assume_wumpus(Stench, [X, Z2]) ; true ),
        ( permitted([Z3, Y]) -> assume_wumpus(Stench, [Z3, Y]) ; true ),
        ( permitted([Z4, Y]) -> assume_wumpus(Stench, [Z4, Y]) ; true )
    ; true
    ).

add_pit_KB(Breeze, VisitedList) :-
    agent_location([X, Y]),
    ( not_member([X, Y], VisitedList) ->
        Z1 is Y + 1, Z2 is Y - 1, Z3 is X + 1, Z4 is X - 1,
        ( permitted([X, Z1]) -> assume_pit(Breeze, [X, Z1]) ; true ),
        ( permitted([X, Z2]) -> assume_pit(Breeze, [X, Z2]) ; true ),
        ( permitted([Z3, Y]) -> assume_pit(Breeze, [Z3, Y]) ; true ),
        ( permitted([Z4, Y]) -> assume_pit(Breeze, [Z4, Y]) ; true )
    ; true
    ).

add_gold_KB(Glitter) :- assume_gold(Glitter).

add_ok_KB([Stench, Breeze], VisitedList) :-
    agent_location([X, Y]),
    ( not_member([X, Y], VisitedList) ->
        Z1 is Y + 1, Z2 is Y - 1, Z3 is X + 1, Z4 is X - 1,
        add_ok_KB_item([X, Z1]),
        add_ok_KB_item([X, Z2]),
        add_ok_KB_item([Z3, Y]),
        add_ok_KB_item([Z4, Y])
    ; true
    ).

add_ok_KB_item(L) :-
    ( permitted(L) ->
        isWumpus(IS_WUMPUS, L),
        isPit(IS_PIT, L),
        assume_ok(IS_WUMPUS, IS_PIT, L)
    ; true
    ).

assume_wumpus(no, L) :-
    retractall(isWumpus(_, L)),
    assert(isWumpus(no, L)).

assume_wumpus(yes, L) :-
    ( isWumpus(no, L) -> true
    ; retractall(isWumpus(_, L)),
      assert(isWumpus(maybe, L))
    ).

assume_pit(no, L) :-
    retractall(isPit(_, L)),
    assert(isPit(no, L)).

assume_pit(yes, L) :-
    ( isPit(no, L) -> true
    ; retractall(isPit(_, L)),
      assert(isPit(maybe, L))
    ).

assume_gold(no) :-
    agent_location(L),
    retractall(isGold(_, L)),
    assert(isGold(no, L)).

assume_gold(yes) :-
    agent_location(L),
    retractall(isGold(_, L)),
    assert(isGold(yes, L)).

assume_ok(no, no, L) :-
    retractall(isOK(_, L)),
    assert(isOK(yes, L)).

assume_ok(maybe, no, L) :-
    ( isOK(yes, L) -> true
    ; retractall(isOK(_, L)),
      assert(isOK(no, L))
    ).

assume_ok(no, maybe, L) :-
    ( isOK(yes, L) -> true
    ; retractall(isOK(_, L)),
      assert(isOK(no, L))
    ).

assume_ok(maybe, maybe, L) :-
    ( isOK(yes, L) -> true
    ; retractall(isOK(_, L)),
      assert(isOK(no, L))
    ).

%------------------------------------------------------------------------------
% Action selection
ask_KB(VisitedList, Action) :-
    agent_location(AL),
    findall(L, (adjacent(L, AL), isOK(yes, L), not_member(L, VisitedList)), PreferredMoves),
    ( PreferredMoves \= [] ->
        member(Action, PreferredMoves) % Choose a preferred unvisited safe move
    ; findall(L, (adjacent(L, AL), isOK(yes, L)), SafeMoves),
      SafeMoves \= [] ->
        member(Action, SafeMoves) % Fallback to any safe move
    ; fail % No safe moves available
    ).

%------------------------------------------------------------------------------
% Utilities
permitted([X, Y]) :-
    world_size(WS),
    X > 0, X =< WS,
    Y > 0, Y =< WS.

not_member(_, []).
not_member([X, Y], [[U, V]|Ys]) :-
    ( X = U, Y = V -> fail
    ; not_member([X, Y], Ys)
    ).

%------------------------------------------------------------------------------
% Initialize game
init :-
    retractall(time_taken(_)),
    assert(time_taken(0)),
    retractall(score(_)),
    assert(score(0)),
    retractall(isWumpus(_, _)),
    retractall(isGold(_, _)),
    retractall(isPit(_, _)),
    retractall(world_size(_)),
    assert(world_size(4)),
    retractall(gold_location(_)),
    assert(gold_location([2, 3])),
    retractall(pit_location(_)),
    assert(pit_location([4, 4])),
    assert(pit_location([3, 3])),
    assert(pit_location([3, 1])),
    retractall(agent_location(_)),
    assert(agent_location([1, 1])),
    retractall(wumpus_location(_)),
    assert(wumpus_location([1, 3])),
    retractall(isOK(_, _)).