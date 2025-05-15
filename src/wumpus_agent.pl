% Usage:
% consult this file
% ?- start.
%
%------------------------------------------------------------------------------
% Prolog program for the Wumpus World
%------------------------------------------------------------------------------
% Declaring dynamic methods
:- dynamic ([
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
    isOK/2,
    arrows/1,
    wumpus_status/2,
    known_wumpus_location/1,
    gold_status/1
]).

%------------------------------------------------------------------------------
% To start the game

start :-
    format('DEBUG: Starting...~n', []),
    clear_kb,
    (tell('kb.txt') ->
        format('DEBUG: kb.txt opened~n', []),
        init,
        format('DEBUG: Initialization complete~n', []),
        take_steps([], 0),
        told,
        format('DEBUG: Finished successfully~n', [])
    ; format('ERROR: Failed to open kb.txt~n', []),
      fail
    ).

clear_kb :-
    % Xóa toàn bộ các facts động (KB cũ)
    retractall(agent_location(_)),
    retractall(gold_location(_)),
    retractall(pit_location(_)),
    retractall(time_taken(_)),
    retractall(score(_)),
    retractall(visited_cells(_)),
    retractall(world_size(_)),
    retractall(wumpus_location(_)),
    retractall(isPit(_, _)),
    retractall(isWumpus(_, _)),
    retractall(isGold(_, _)),
    retractall(isOK(_, _)),
    retractall(arrows(_)),
    retractall(wumpus_status(_, _)),
    retractall(known_wumpus_location(_)),
    retractall(gold_status(_)).


%------------------------------------------------------------------------------
% Scheduling simulation:

step_pre(VisitedList, Steps) :-
    agent_location(AL),
    wumpus_location(WL),
    pit_location(PL),
    score(S),
    time_taken(T),
    wumpus_status(WL, WS),
    gold_status(GS),
    % Check for loss or win conditions
    ( GS = grabbed ->
        writeln('WON!'),
        format('Score: ~p,~n Time: ~p~n', [S,T])
    ; AL=WL, WS=alive ->
        format('Lost: Wumpus eats you!~n', []),
        format('Score: ~p,~n Time: ~p~n', [S,T])
    ; AL=PL ->
        format('Lost: you fell into the pit!~n', []),
        format('Score: ~p,~n Time: ~p~n', [S,T])
    ; take_steps(VisitedList, Steps)
    ).

take_steps(VisitedList, Steps) :-
    Steps < 100,
    NewSteps is Steps + 1,
    format('~n~n~n', []),
    agent_location(AL),
    format('New Round: I am at ~p and I have visited ~p~n', [AL,VisitedList]),

    retractall( isOK(_, AL) ),
    assert( isOK(yes, AL) ),
    retractall( isPit(_, AL) ),
    assert( isPit(no, AL) ),
    retractall( isWumpus(_, AL) ),
    assert( isWumpus(no, AL) ),
    retractall( isGold(_, AL) ),
    assert( isGold(no, AL) ),

    make_percept_sentence(Perception),
    format('I\'m in ~p, seeing: ~p~n', [AL,Perception]),

    update_KB(Perception, VisitedList),
    VL = [AL|VisitedList],
    ( ask_KB(VL, Action) ->
        ( Action = shoot(WL) ->
            format('I shoot an arrow at ~p!~n', [WL]),
            shoot_arrow(WL)
        ; Action = grab ->
            format('I grab the gold!~n', []),
            grab_gold
        ; format('I\'m going to: ~p~n', [Action]),
          update_agent_location(Action)
        )
    ; format('Error: No valid action found~n', []),
      fail
    ),

    update_time,
    update_score,

    % Check if gold is grabbed after action
    gold_status(GS),
    score(S),
    time_taken(T),
    ( GS = grabbed ->
        format('Checking standing: Gold grabbed, ending game!~n', []),
        standing,
        writeln('WON!'),
        format('Score: ~p,~n Time: ~p~n', [S,T]),
        halt
    ; format('VisitedList = ~p~n', [VL]),
      standing,
      step_pre(VL, NewSteps)
    ).

take_steps(_, Steps) :-
    Steps >= 100, % Kiểm tra nếu vượt quá 30 bước
    format('Error: Maximum steps (30) reached, possible infinite loop~n', []),
    score(S),
    time_taken(T),
    format('Score: ~p,~n Time: ~p~n', [S,T]),
    halt.
%------------------------------------------------------------------------------
% Arrow shooting

shoot_arrow(WL) :-
    wumpus_location(WL),
    retractall(wumpus_status(WL, _)),
    assert(wumpus_status(WL, dead)),
    retractall(arrows(_)),
    assert(arrows(0)),
    retractall(isWumpus(_, WL)),
    assert(isWumpus(no, WL)),
    retractall(isOK(_, WL)),
    assert(isOK(yes, WL)),
    format('Wumpus at ~p is killed!~n', [WL]),
    format('KB learn ~p is now OK~n', [WL]),
    update_score(-10).

%------------------------------------------------------------------------------
% Gold grabbing

grab_gold :-
    agent_location(AL),
    gold_location(GL),
    AL = GL,
    retractall( gold_status(_) ),
    assert( gold_status(grabbed) ),
    retractall( isGold(_, AL) ),
    assert( isGold(yes, AL) ),
    format('KB learn ~p - GOT THE GOLD!!!~n', [AL]),
    update_score(1000).

%------------------------------------------------------------------------------
% Updating states

update_time :-
    time_taken(T),
    NewTime is T+1,
    retractall( time_taken(_) ),
    assert( time_taken(NewTime) ),
    format('New time: ~p~n', [NewTime]).



update_score(P) :-
    score(S),
    NewScore is S+P,
    retractall( score(_) ),
    assert( score(NewScore) ),
    format('New score: ~p~n', [NewScore]).

update_score:-
    update_score(-1).

update_agent_location(NewAL) :-
    retractall( agent_location(_) ),
    assert( agent_location(NewAL) ),
    format('New Agent Location: ~p~n', [NewAL]).

is_pit(no, X) :-
    \+ pit_location(X).
is_pit(yes, X) :-
    pit_location(X).

%------------------------------------------------------------------------------
% Display standings

standing :-
    wumpus_location(WL),
    gold_location(GL),
    agent_location(AL),
    wumpus_status(WL, WS),
    gold_status(GS),
    format('Checking standing: AL=~p, WL=~p, WS=~p, GS=~p~n', [AL, WL, WS, GS]),
    ( is_pit(yes, AL) -> format('Agent has fallen into a pit!~n', []), fail
    ; stnd(AL, GL, WL, WS, GS)
    ).

stnd(AL, _, AL, alive, _) :-
    format('YIKES! You\'re eaten by the wumpus!', []),
    fail.
stnd(_, _, _, _, grabbed) :-
    format('AGENT GRABBED THE GOLD!!~n', []),
    true.
stnd(_, _, _, _, _) :-
    format('There\'s still something to do...~n', []).

%------------------------------------------------------------------------------
% Perception

make_percept_sentence([Stench,Breeze,Glitter]) :-
    format('make_percept_sentence... ~p,~p,~p ~n', [Stench,Breeze,Glitter]),
    smelly(Stench),
    format('Stench... ~p ~n', [Stench]),
    breezy(Breeze),
    glittering(Glitter).

%------------------------------------------------------------------------------
% Initializing

% Thay thế phần init bằng:
init :-
    init_game,
    (current_prolog_flag(argv, [InputFile|_]) -> 
        open(InputFile, read, Stream)
    ;
        open('init_data.txt', read, Stream)
    ),
    read(Stream, WorldSize), assert(world_size(WorldSize)),
    read(Stream, WumpusList), forall(member(Pos, WumpusList), assert_wumpus(Pos)),
    read(Stream, PitList), forall(member(Pos, PitList), assert_pit(Pos)),
    read(Stream, GoldPos), assert(gold_location(GoldPos)),
    close(Stream),
    init_agent,
    init_kb.

assert_wumpus(Pos) :-
    assertz(wumpus_location(Pos)),
    assertz(wumpus_status(Pos, alive)).

assert_pit(Pos) :-
    assertz(pit_location(Pos)).

init_game :-
    retractall( time_taken(_) ),
    assert( time_taken(0) ),
    retractall( score(_) ),
    assert( score(0) ),
    retractall( isWumpus(_,_) ),
    retractall( isGold(_,_) ),
    retractall( visited_cells(_) ),
    assert( visited_cells([]) ),
    retractall( arrows(_) ),
    assert( arrows(10) ),
    forall(wumpus_location(Pos), assert(wumpus_status(Pos, alive))),
    retractall( known_wumpus_location(_) ),
    retractall( gold_status(_) ),
    assert( gold_status(present) ).

init_land_fig72 :-
    retractall( isPit(_, _) ),
    assert( isPit(maybe,[3,1]) ),
    retractall( world_size(_) ),
    assert( world_size(4) ),
    retractall( gold_location(_) ),
    assert( gold_location([3,2]) ),
    retractall( pit_location(_) ),
    assert( pit_location([4,4]) ),
    assert( pit_location([3,3]) ),
    assert( pit_location([3,1]) ).

init_kb :-
    retractall(isOK(_,_)),
    assert(isOK(yes, [1,1])).

init_agent :-
    retractall( agent_location(_) ),
    assert( agent_location([1,1]) ).

init_wumpus :-
    retractall(wumpus_location(_)),
    current_input(Input),  % lấy từ `kb.txt` hoặc do UI inject vào
    read(Input, WumpusList),
    forall(member(Pos, WumpusList), assert(wumpus_location(Pos))).

%------------------------------------------------------------------------------
% Perceptors (Sensors)

adjacent([X1, Y1], [X2, Y2]) :-
    permitted([X2, Y2]),
    ( (X1 =:= X2, abs(Y1 - Y2) =:= 1)
    ; (Y1 =:= Y2, abs(X1 - X2) =:= 1)
    ).



isSmelly(Ls1) :-
    once((
        wumpus_location(WL),
        wumpus_status(WL, alive),
        adjacent(Ls1, WL)
    )).


isBreezy(Ls1) :-
    pit_location(Ls2),
    permitted(Ls2),
    adjacent(Ls1, Ls2).

isGlittering([X1, Y1]) :-
    gold_location([X2, Y2]),
    gold_status(present),
    X1 = X2,
    Y1 = Y2.

breezy(yes) :-
    agent_location(AL),
    isBreezy(AL).
breezy(no) :-
    agent_location(AL),
    \+ isBreezy(AL).

smelly(yes) :-
    agent_location(AL),
    isSmelly(AL),
    format('smelly=yes ~n', []).
smelly(no) :-
    agent_location(AL),
    \+ isSmelly(AL),
    format('smelly=no ~n', []).

glittering(yes) :-
    agent_location(AL),
    isGlittering(AL).
glittering(no) :-
    agent_location(AL),
    \+ isGlittering(AL).

%------------------------------------------------------------------------------
% Knowledge Base:

update_KB([Stench,Breeze,Glitter], VisitedList) :-
    format('update_KB ~p~n', [[Stench,Breeze,Glitter]]),
    add_wumpus_KB(Stench,VisitedList),
    add_pit_KB(Breeze,VisitedList),
    add_gold_KB(Glitter),
    add_ok_KB([Stench,Breeze], VisitedList),
    update_known_wumpus_location.

update_known_wumpus_location :-
    findall(L, (isWumpus(maybe, L), permitted(L)), MaybeWumpus),
    format('Maybe Wumpus locations: ~p~n', [MaybeWumpus]),
    ( MaybeWumpus = [WL] ->
        retractall(known_wumpus_location(_)),
        assert(known_wumpus_location(WL)),
        format('KB learn Wumpus is definitely at ~p~n', [WL])
    ; true
    ).

add_ok_KB([Stench,Breeze], VisitedList) :-
    format('add_ok_KB ~p,~p~n', [Stench,Breeze]),
    agent_location([X,Y]),
    ( not_member([X,Y], VisitedList) ->
        format('Not visited before= ~p~n', [[X,Y]]),
        Z1 is Y+1,
        Z2 is Y-1,
        Z3 is X+1,
        Z4 is X-1,
        add_ok_KB_item([X,Z1]),
        add_ok_KB_item([X,Z2]),
        add_ok_KB_item([Z3,Y]),
        add_ok_KB_item([Z4,Y])
    ; format('Already visited before= ~p~n', [[X,Y]])
    ).

add_ok_KB_item(L) :-
    format('add_ok_KB_item ~p~n', [L]),
    ( permitted(L) ->
        isWumpus(IS_WUMPUS,L),
        isPit(IS_PIT,L),
        assume_ok(IS_WUMPUS,IS_PIT,L)
    ; format('~p is not permitted~n', [L])
    ).

add_wumpus_KB(Stench,VisitedList) :-
    format('add_wumpus_KB ~p~n', [Stench]),
    agent_location([X,Y]),
    ( not_member([X,Y], VisitedList) ->
        format('Not visited before= ~p~n', [[X,Y]]),
        Z1 is Y+1,
        Z2 is Y-1,
        Z3 is X+1,
        Z4 is X-1,
        ( permitted([X,Z1]) -> assume_wumpus(Stench,[X,Z1]) ; format('~p is not permitted~n', [[X,Z1]]) ),
        ( permitted([X,Z2]) -> assume_wumpus(Stench,[X,Z2]) ; format('~p is not permitted~n', [[X,Z2]]) ),
        ( permitted([Z3,Y]) -> assume_wumpus(Stench,[Z3,Y]) ; format('~p is not permitted~n', [[Z3,Y]]) ),
        ( permitted([Z4,Y]) -> assume_wumpus(Stench,[Z4,Y]) ; format('~p is not permitted~n', [[Z4,Y]]) )
    ; format('Already visited before= ~p~n', [[X,Y]])
    ).

add_pit_KB(Breeze,VisitedList) :-
    format('add_pit_KB ~p~n', [Breeze]),
    agent_location([X,Y]),
    ( not_member([X,Y], VisitedList) ->
        format('Not visited before= ~p~n', [[X,Y]]),
        Z1 is Y+1,
        Z2 is Y-1,
        Z3 is X+1,
        Z4 is X-1,
        ( permitted([X,Z1]) -> assume_pit(Breeze,[X,Z1]) ; format('~p is not permitted~n', [[X,Z1]]) ),
        ( permitted([X,Z2]) -> assume_pit(Breeze,[X,Z2]) ; format('~p is not permitted~n', [[X,Z2]]) ),
        ( permitted([Z3,Y]) -> assume_pit(Breeze,[Z3,Y]) ; format('~p is not permitted~n', [[Z3,Y]]) ),
        ( permitted([Z4,Y]) -> assume_pit(Breeze,[Z4,Y]) ; format('~p is not permitted~n', [[Z4,Y]]) )
    ; format('Already visited before= ~p~n', [[X,Y]])
    ).

add_gold_KB(Glitter) :-
    format('add_gold_KB ~p~n', [Glitter]),
    agent_location(L),
    gold_status(GS),
    ( Glitter = yes, GS = present ->
        retractall( isGold(_, L) ),
        assert( isGold(yes, L) ),
        format('KB learn ~p - glitter detected!~n', [L])
    ; retractall( isGold(_, L) ),
      assert( isGold(no, L) ),
      format('KB learn ~p - there is no gold here!~n', [L])
    ).

assume_wumpus(no, L) :-
    retractall( isWumpus(_, L) ),
    assert( isWumpus(no, L) ),
    format('KB learn ~p - no Wumpus there!~n', [L]).

assume_wumpus(yes, L) :-
    format('KB learn ~p - is it a Wumpus?~n', [L]),
    ( isWumpus(no, L) ->
        format('I know there is no Wumpus at ~p!~n',[L])
    ; retractall( isWumpus(_, L) ),
      assert( isWumpus(maybe, L) ),
      format('KB learn ~p - maybe there is a Wumpus!~n', [L])
    ).

assume_pit(no, L) :-
    retractall( isPit(_, L) ),
    assert( isPit(no, L) ),
    format('KB learn ~p - there is no Pit there!~n', [L]).

assume_pit(yes, L) :-
    format('KB learn ~p - is it a Pit?~n', [L]),
    ( isPit(no, L) ->
        format('I know there is no Pit at ~p!~n',[L])
    ; retractall( isPit(_, L) ),
      assert( isPit(maybe, L) ),
      format('KB learn ~p - maybe there is a Pit!~n', [L])
    ).

assume_ok(no,no,L) :-
    format('assume_ok(no,no,L) ~p~n', [L]),
    retractall( isOK(_, L) ),
    assert( isOK(yes, L) ),
    format('KB learn ~p is OK~n', [L]).

assume_ok(maybe,no,L) :-
    format('assume_ok(maybe,no,L) ~p~n', [L]),
    retractall( isOK(_, L) ),
    assert( isOK(no, L) ),
    format('KB learn ~p is NOT OK~n', [L]).

assume_ok(no,maybe,L) :-
    format('assume_ok(no,maybe,L) ~p~n', [L]),
    retractall( isOK(_, L) ),
    assert( isOK(no, L) ),
    format('KB learn ~p is NOT OK~n', [L]).

assume_ok(maybe,maybe,L) :-
    format('assume_ok(maybe,maybe,L) ~p~n', [L]),
    retractall( isOK(_, L) ),
    assert( isOK(no, L) ),
    format('KB learn ~p is NOT OK~n', [L]).

permitted([X,Y]) :-
    world_size(WS),
    0 < X, X < WS+1,
    0 < Y, Y < WS+1.

%------------------------------------------------------------------------------
% Action selection based on KB

ask_KB(VisitedList, Action) :-
    format('ask_KB VisitedList=~p - Action=~p~n', [VisitedList,Action]),
    agent_location(AL),
    gold_location(GL),
    gold_status(GS),
    make_percept_sentence([_,_,Glitter]),
    format('agent_location=~p, Glitter=~p~n', [AL,Glitter]),
    ( AL = GL, Glitter = yes, GS = present ->
        format('Glitter detected at ~p, grabbing gold!~n', [AL]),
        Action = grab
    ; known_wumpus_location(WL),
      adjacent(AL, WL),
      arrows(N), N > 0,
      wumpus_status(WL, alive) ->
        format('I know the Wumpus is at ~p and I\'m adjacent!~n', [WL]),
        Action = shoot(WL)
    ; findall([Pref,L], preferred_move(Pref,VisitedList,L), Moves),
      format('Available moves: ~p~n', [Moves]),
      select_best_move(Moves, VisitedList, AL, Action),
      format('Selected move to ~p~n', [Action]),
      adjacent(Action, AL),
      format('Action=~p is adjacent to AL=~p~n', [Action,AL])
    ).

select_best_move(Moves, VisitedList, AL, L) :-
    length(VisitedList, Len),
    ( Moves \= [],
      ( Len < 2, % Match original behavior: prefer visited cell early
        member([no,L], Moves),
        not_in_cycle(L, VisitedList),
        adjacent(L, AL) ->
          format('Choosing safe visited cell (short history) ~p~n', [L])
      ; member([yes,L], Moves),
        not_in_cycle(L, VisitedList),
        adjacent(L, AL) ->
          format('Choosing unvisited safe cell ~p~n', [L])
      ; member([no,L], Moves),
        not_in_cycle(L, VisitedList),
        adjacent(L, AL) ->
          format('Choosing safe visited cell (least visited) ~p~n', [L])
      ; member([_,L], Moves),
        adjacent(L, AL) ->
          format('Choosing safe cell (no better options) ~p~n', [L])
      )
    ; format('No safe moves, failing~n', []),
      fail
    ).

% Avoid cycles by preferring cells not part of a repeating pattern
not_in_cycle(L, VisitedList) :-
    count_visits(L, VisitedList, Count),
    Count < 2,
    \+ detect_cycle(VisitedList).

% Count number of times a cell appears in VisitedList
count_visits(L, VisitedList, Count) :-
    findall(1, member(L, VisitedList), Ones),
    length(Ones, Count).

% Detect cycles (e.g., [A,B,A,B] or [A,B,C,A])
detect_cycle(VisitedList) :-
    append(_, [A,B|Rest], VisitedList),
    member(A, Rest),
    A \= B.

preferred_move(yes,VisitedList,L) :-
    isOK(yes,L),
    format('preferred_move - Let\'s see if ~p is OK~n', [L]),
    not_member(L,VisitedList),
    format('preferred_move - L was not visited before= ~p~n', [L]).

preferred_move(no,_,L) :-
    isOK(yes,L),
    format('preferred_move - Let\'s see if ~p is OK~n', [L]).

%------------------------------------------------------------------------------
% Utils

not_member(_, []).
not_member([X,Y], [[U,V]|Ys]) :-
    ( X=U,Y=V -> fail
    ; not_member([X,Y], Ys)
    ).