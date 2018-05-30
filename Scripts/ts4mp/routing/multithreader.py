import time
import gsi_handlers.routing_handlers
import elements
import sims4
from ts4mp.debug.log import ts4mp_log
from threading import Lock

import interactions.utils.routing
from element_utils import soft_sleep_forever
import routing
#ts4mp.reload Mods/ts4multiplayer/Scripts/ts4mp/routing/multithreader

gsi_handlers.routing_handlers.archiver._archive_enabled = True
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification

def show_notif(time):
    return
    try:
        notification = UiDialogNotification.TunableFactory().default(services.get_active_sim(), text=lambda **_: LocalizationHelperTuning.get_raw_text("Total time spent so far: {} s".format(time)))
        notification.show_dialog()

    except Exception as e:
        ts4mp_log("errors", str(e))

def show_notif2(time):
    return
    notification = UiDialogNotification.TunableFactory().default(services.get_active_sim(), text=lambda **_: LocalizationHelperTuning.get_raw_text("Transition time so far: {} s".format(time)))
    notification.show_dialog()


def show_notif3(time):
    notification = UiDialogNotification.TunableFactory().default(services.get_active_sim(), text=lambda **_: LocalizationHelperTuning.get_raw_text("Autonomy time: {0:.4} s".format(time)))
    notification.show_dialog()
total_time = 0
def archive_plan(planner, path, ticks, time):
    global total_time
    total_time += time
    if time > 0.01:
        show_notif(total_time)
    ts4mp_log("Path plan time", "Plan Time, Ticks: {}, {}".format(time, ticks))

import services

gsi_handlers.routing_handlers.archive_plan = archive_plan

cloud_paths_lock = Lock()
cloud_paths = []




# TODO: Complete overhaul and streamlined L18N support
from ts4mp.debug.log import ts4mp_log


paths_enabled = False
total_p_time = 0
class Timer():
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.t1 = time.time()

    def __exit__(self, *args):
        global total_p_time

        self.t2 = time.time()
        if self.name == "Transition Sequence":

            total_p_time += self.t2 - self.t1

        if (self.t2 - self.t1) * 1000 > 20:
            if self.name == "Transition Sequence":
                show_notif2(total_p_time)
                
        if self.name == "Autonomy":
                show_notif3(self.t2 - self.t1) 
                
        if (self.t2 - self.t1) * 1000 > 20:
            ts4mp_log(self.name, "time: ,{0:.2f}".format(self.t2 - self.t1))

import _pathing
def generate_path(self, timeline):
    #ts4mp_log("Path plan time", "Starting path")

    start_time = time.time()
    ticks = 0
    try:
        self.path.status = routing.Path.PLANSTATUS_PLANNING

        self.path.nodes.clear_route_data()
        if not self.route.goals:
            self.path.status = routing.Path.PLANSTATUS_FAILED
        else:
            for goal in self.route.goals:
                self.path.add_goal(goal)
            for origin in self.route.origins:
                self.path.add_start(origin)
            for (waypoint_group, waypoints) in enumerate(self.route.waypoints):
                for waypoint in waypoints:
                    waypoint.group = waypoint_group
                    self.path.add_waypoint(waypoint)
            self.sim.routing_component.on_plan_path(self.route.goals, True)
            if paths_enabled:
                if self.path.nodes.make_path() is True:
                    plan_in_progress = True

                    def is_planning_done():
                        #ts4mp_log("Path plan time", "Calculating path")

                        nonlocal ticks, plan_in_progress
                        ticks += 1
                        plan_in_progress = self.path.nodes.plan_in_progress
                        return not plan_in_progress

                    yield from element_utils.run_child(timeline, elements.BusyWaitElement(soft_sleep_forever(), is_planning_done))
                    if plan_in_progress:
                        self.path.status = routing.Path.PLANSTATUS_FAILED
                    else:
                        #ts4mp_log("Path plan time", "Done with path")

                        self.path.nodes.finalize(self._is_failure_route)
                else:
                    self.path.status = routing.Path.PLANSTATUS_FAILED
            else:
                try:
                    #ts4mp_log("errors", dir(self.path.nodes))
                    routing_location_start = routing.Location(origin.position, origin.orientation,
                                                        origin.routing_surface_id)
                    routing_location = routing.Location(goal.position, goal.orientation,
                                                        goal.routing_surface_id)
                    walkstyle = sims4.hash_util.hash32("walk")

                    self.path.nodes.add_node(routing_location_start, 0, 0, walkstyle)
                    self.path.nodes.add_node(routing_location, 5, 0, walkstyle)


                except Exception as e:
                    ts4mp_log("errors", str(e))
     

            new_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
            new_route.path.copy(self.route.path)
            new_path = routing.Path(self.path.sim, new_route)
            new_path.status = self.path.status
            new_path._start_ids = self.path._start_ids
            #ts4mp_log("errors", dir(self.path.nodes[0]))
            #new_path._start_ids = [self.path.nodes[0].handle]


            new_path._goal_ids = self.path._goal_ids
            #new_path._goal_ids = [self.path.nodes[1].handle]

            result_path = new_path
            if gsi_handlers.routing_handlers.archiver.enabled:
                gsi_handlers.routing_handlers.archive_plan(self.sim, self.path, ticks, (time.time() - start_time))
            num_nodes = len(new_path.nodes)
            self.route = result_path.route
            self.path = result_path
            self.sim.routing_component.on_plan_path(self.route.goals, False)
    except Exception:
        self.path.status = routing.Path.PLANSTATUS_FAILED
        self.sim.routing_component.on_plan_path(self.route.goals, False)
    if self.path.status == routing.Path.PLANSTATUS_PLANNING:
        self.path.set_status(routing.Path.PLANSTATUS_READY)
    else:
        self.path.set_status(routing.Path.PLANSTATUS_FAILED)

def selected_start(self):
    (start_id, _) = self.nodes.selected_start_tag_tuple
    if start_id == 0:
        for thing in self._start_ids:
            return self._start_ids[thing]
    return self._start_ids[start_id]

def selected_goal(self):
    (goal_id, _) = self.nodes.selected_tag_tuple
    if goal_id == 0:
        for thing in self._goal_ids:
            return self._goal_ids[thing]
    return self._goal_ids[goal_id]


routing.Path.selected_start = property(selected_start)
routing.Path.selected_goal = property(selected_goal)

interactions.utils.routing.PlanRoute.generate_path = generate_path
from sims4.commands import CommandType
from _math import Vector3
from elements import GeneratorElement
from interactions.utils.routing import PlanRoute, FollowPath
from objects.components.types import ROUTING_COMPONENT
import element_utils
import routing
import services
import sims4.commands



@sims4.commands.Command('print_position', command_type=CommandType.Live)
def print_position(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output(str(services.get_active_sim().position))

@sims4.commands.Command('sf', command_type=CommandType.Live)
def routing_debug_follow( _connection=None):
    try:
        obj = services.get_active_sim()
        if obj is None:
            return False
        routing_component = obj.get_component(ROUTING_COMPONENT)
        if routing_component is None:
            return False
        pos = services.get_active_sim().position
        x = pos.x + 5
        y = pos.y 
        z = pos.z

        def _do_route_gen(timeline):
            try:
                with Timer("path planning"):
                    location = routing.Location(Vector3(x, y, z), routing_surface=obj.routing_surface)
                    goal = routing.Goal(location)
                    routing_context = obj.get_routing_context()
                    route = routing.Route(obj.routing_location, (goal,), routing_context=routing_context)
                    plan_primitive = PlanRoute(route, obj)
                    result = yield from element_utils.run_child(timeline, plan_primitive)
                    if not result:
                        return result
                    nodes = plan_primitive.path.nodes
                    if not nodes or not nodes.plan_success:
                        return False
                    follow_path_element = FollowPath(obj, plan_primitive.path)
                    result = yield from element_utils.run_child(timeline, follow_path_element)
                    if not result:
                        return result
                    return True
            except Exception as e:
                ts4mp_log("errors", str(e))
        timeline = services.time_service().sim_timeline
        timeline.schedule(GeneratorElement(_do_route_gen))
        return True
    except Exception as e:
        ts4mp_log("errors", str(e))

import interactions.base.super_interaction
from autonomy.autonomy_util import AutonomyAffordanceTimes
from sims4.log import Logger
import time
import algos
logger = Logger('Sleep5')
import animation.animation_sleep_element
import clock, element_utils, elements
from animation.animation_drift_monitor import build_animation_drift_monitor_sequence
import element_utils

from scheduling import MAX_ELEMENTS, MAX_GARBAGE_FACTOR, ACCEPTABLE_GARBAGE, HardStopError, raise_exception
import time
import inspect
import scheduling
import heapq
from sims4.callback_utils import CallableListConsumingExceptions


def simulate(self, until, max_elements=MAX_ELEMENTS, max_time_ms=None):
    try:
        #logger.debug("Starting.")
        if until < self.future:
            return True
        count = 0
        self.future = until
        self.per_simulate_callbacks()
        if max_time_ms is not None:
            start_time = time.monotonic()
            end_time = start_time + max_time_ms/1000
            end_time = None
        else:
            end_time = None
        early_exit = False
        #logger.debug("Going into heap.")

        while self.heap:
            #logger.debug("Something in the heap.")

            if self.heap[0].when <= until:
                count += 1
                #ts4mp_log("Path plan time", "Popping element from the heap.")

                handle = heapq.heappop(self.heap)
                if handle.element is None:
                    continue
                #logger.debug("Getting handle information.")

                (when, _, _t, _s, e) = handle
                # if "_process_gen@491;" in str(e):
                    # continue
                if self.now != when:
                    self.now = when
                    self.on_time_advanced()
                calling = True
                result = None
                try:
                    #logger.debug("Attempting to execute handle.")

                    while e is not None:
                        handle._set_when(None)
                        handle._set_scheduled(False)
                        self._active = (e, handle)
                        try:
                            if calling:
                                result = e._run(self)
                            else:
                                result = e._resume(self, result)
                            if self._pending_hard_stop:
                                raise HardStopError('Hard stop exception was consumed by {}'.format(e))
                        except BaseException as exc:
                            self._pending_hard_stop = False
                            self._active = None
                            try:
                                self._report_exception(e, exc, 'Exception {} Element'.format('running' if calling else 'resuming'))
                            finally:
                                if e._parent_handle is not None:
                                    self.hard_stop(e._parent_handle)
                        if inspect.isgenerator(result):
                            raise RuntimeError('Element {} returned a generator {}'.format(e, result))
                        if self._active is None:
                            break
                        if self._child is not None:
                            handle = self._child
                            self._child = None
                            e = handle.element
                            calling = True
                            count += 1
                            continue
                        if handle.is_scheduled:
                            break
                        e._element_handle = None
                        handle = e._parent_handle
                        e._parent_handle = None
                        if handle is None:
                            e._teardown()
                            break
                        child = e
                        e = handle.element
                        will_reschedule = e._child_returned(child)
                        if not will_reschedule:
                            child._teardown()
                        del child
                        calling = False
                finally:
                    self._active = None
                    self._child = None
                if count >= max_elements:
                    early_exit = True
                    break
                if end_time is not None and time.monotonic() > end_time:
                    early_exit = True
                    break
            else:
                break
        if self._garbage > ACCEPTABLE_GARBAGE and self._garbage > len(self.heap)*MAX_GARBAGE_FACTOR:
            self._clear_garbage()
        if not early_exit:
            if self.now != until:
                self.now = until
                self.on_time_advanced()
            return True
        return False
    except Exception as e:
        ts4mp_log("errors", str(e))
import distributor
import math

@sims4.commands.Command('toggle_paths', command_type = CommandType.Live)
def toggle_paths(_connection=None):
    global paths_enabled
    output = sims4.commands.CheatOutput(_connection)
    paths_enabled = not paths_enabled
    if paths_enabled:
        output("Enabled pathfinding")
        return
    output("Disabled pathfinding")
@sims4.commands.Command('sims.test_path', command_type = CommandType.Live)
def test_path(walkstyle_name='walk', _connection=None):
    obj = services.get_active_sim()
    try:
        if obj is not None:
            route = routing.Route(routing.Location(obj.location.transform.translation, obj.location.transform.orientation, obj.location.routing_surface), ())
            path = routing.Path(obj, route)
            path.status = routing.Path.PLANSTATUS_READY
            start_pos = obj.location.transform.translation
            last_pos = start_pos
            start_surface = obj.location.routing_surface
            walkstyle = sims4.hash_util.hash32(walkstyle_name)
            (walk_duration, walk_distance) = routing.get_walkstyle_info(walkstyle, obj.age, obj.gender, obj.species)
            speed = walk_distance/walk_duration
            a = 2.5
            b = 0.1
            last_time = 0
            for i in range(51):
                angle = i*0.25120000000000003
                x = (a + b*angle)*math.cos(angle)
                y = (a + b*angle)*math.sin(angle)
                pos = sims4.math.Vector3(start_pos.x + x, start_pos.y + i*0.1, start_pos.z + y)
                dir = pos - last_pos
                orientation = sims4.math.Quaternion.from_forward_vector(dir)
                if i == 0:
                    path.nodes.add_node(routing.Location(start_pos, orientation, start_surface), 0, 0, walkstyle)
                time = last_time + dir.magnitude()/speed
                path.nodes.add_node(routing.Location(pos, orientation, start_surface), time, 0, walkstyle)
                last_time = time
                last_pos = pos
            pos = sims4.math.Vector3(start_pos.x, start_pos.y, start_pos.z)
            dir = pos - last_pos
            orientation = sims4.math.Quaternion.from_forward_vector(dir)
            time = last_time + dir.magnitude()/speed
            path.nodes.add_node(routing.Location(pos, orientation, start_surface), time, 0, walkstyle)
            zone_id = obj.zone_id
            zone = services._zone_manager.get(zone_id)
            start_time = services.game_clock_service().monotonic_time()
            op = distributor.ops.FollowRoute(obj, path, start_time)
            distributor.ops.record(obj, op)
            final_path_node = path.nodes[-1]
            final_position = sims4.math.Vector3(*final_path_node.position)
            final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
            transform = sims4.math.Transform(final_position, final_orientation)
            obj.location = obj.location.clone(routing_surface=start_surface, transform=transform)
    except Exception as e:
        ts4mp_log("errors", str(e))
scheduling.Timeline.simulate = simulate
import interactions.base.super_interaction
from autonomy.autonomy_util import AutonomyAffordanceTimes

def _estimate_distance(self, ignore_all_other_sis):
    with Timer("Transition Sequence"):
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.TRANSITION_SEQUENCE):
            self._generate_connectivity(ignore_all_other_sis=ignore_all_other_sis)
    with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.DISTANCE_ESTIMATE):
        try:
            result = self.transition.estimate_distance_for_current_progress()
        finally:
            if ignore_all_other_sis:
                self.transition = None
        return result
        
def estimate_final_path_distance(self, timeline, ignore_all_other_sis):
    with Timer("Transition Sequence"):
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.TRANSITION_SEQUENCE):
            yield self._generate_routes(timeline, ignore_all_other_sis=ignore_all_other_sis)
    with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.DISTANCE_ESTIMATE):
        try:
            result = self.transition.estimate_distance_for_current_progress()
        finally:
            if ignore_all_other_sis:
                self.transition = None
        return result
@classmethod
def update_adaptive_speed(cls):
    return
interactions.base.super_interaction.SuperInteraction._estimate_distance = _estimate_distance
interactions.base.super_interaction.SuperInteraction.estimate_final_path_distance = estimate_final_path_distance
import adaptive_clock_speed
adaptive_clock_speed.AdaptiveClockSpeed.update_adaptive_speed = update_adaptive_speed
import autonomy.autonomy_exceptions
import autonomy.autonomy_service
import autonomy.autonomy_modes

log = ""
trace_count = 0
def tracefunc(frame, event, arg, indent=[0]):
    global log 
    global trace_count
    

    if event == "call":
        indent[0] += 2
        to_print =  "-" * indent[0] + "> call function " +  frame.f_code.co_name
        log += to_print + "\n"
    elif event == "return":
        to_print =  "<" + "-" * indent[0] +  "exit function " + frame.f_code.co_name
        log += to_print + "\n"

        indent[0] -= 2
        
    if trace_count % 100000 == 0:
        ts4mp_log("time", log)
        
    return tracefunc

import sys
def _update_gen(self, timeline):
    with Timer("Autonomy"):
        #sys.setprofile(None)
        while self.queue:
            cur_request = self.queue.pop(0)
            cur_request.autonomy_mode.set_process_start_time()
            try:
                next_sim = cur_request.sim
                if next_sim is not None:
                    self._active_sim = next_sim
                    yield from self._execute_request_gen(timeline, cur_request, self.MAX_SECONDS_PER_LOOP)
                else:
                    pass
            except autonomy.autonomy_exceptions.AutonomyExitException:
                pass
            finally:
                cur_request.sleep_element.trigger_soft_stop()
                cur_request.sleep_element = None
                self._update_automation_load_test()
                self._check_for_automated_performance_test_sim()
                self._active_sim = None
            sleep_element = element_utils.sleep_until_next_tick_element()
            yield timeline.run_child(sleep_element)
            #sys.setprofile(None)

def run_stuff(self, generat):
    for thing in generat:
        ts4mp_log("Modes", thing)

        yield thing 


            
            
def run_gen(self, timeline, timeslice):

    self._motive_scores = self._score_motives()
    #ts4mp_log("Modes", str(self._motive_scores))
    generat = self._run_gen(timeline, timeslice)
    ts4mp_log("Modes", type(self))
    with Timer("Modes"):
        pass
        # for value in generat:
            # ts4mp_log("Modes", value)

    #result = yield from self._run_gen(timeline, timeslice)
    #result = yield from run_stuff(self, generat)
    result = yield from self._run_gen(timeline, timeslice)

    return result
from _weakrefset import WeakSet
  
def _dont_timeslice_gen(timeline):
    return False

    yield None
    
    

from autonomy.autonomy_interaction_priority import AutonomyInteractionPriority
import itertools
import date_and_time
import random
from autonomy.autonomy_modes import AutonomyMode
timeslice_logger = sims4.log.Logger('AutonomyTimeslice', default_owner='rez')
def block_until_done(timeline):
    return False
import random
def _run_gen(self, timeline, timeslice):
    try:
        #ts4mp_log("potential", "start")

        if self._should_log(self._sim):
            logger.debug('Processing {}', self._sim)
        gsi_enabled_at_start = gsi_handlers.autonomy_handlers.archiver.enabled
        if gsi_enabled_at_start:
            if self._gsi_objects is None:
                self._gsi_objects = []
            if self._gsi_interactions is None:
                self._gsi_interactions = []
        self._actively_scored_motives, motives_to_score = self._get_motives_to_score()
        if not self._actively_scored_motives and not self._request.object_list:
            return
        else:
            self._motives_being_solved = self._get_all_motives_currently_being_solved()
            if timeslice is None:
                timeslice_if_needed_gen = _dont_timeslice_gen
            else:
                start_time = time.clock()

                def timeslice_if_needed_gen(timeline):
                    nonlocal start_time
                    time_now = time.clock()
                    elapsed_time = time_now - start_time
                    if elapsed_time < timeslice:
                        return False
                    if self._timestamp_when_timeslicing_was_removed is not None:
                        enable_long_slice = False
                    else:
                        total_elapsed_time = time_now - self._process_start_time
                        if total_elapsed_time > self.MAX_REAL_SECONDS_UNTIL_TIMESLICING_IS_REMOVED:
                            timeslice_logger.debug('Autonomy request for {} took too long; timeslicing is removed.', self._sim)
                            self._timestamp_when_timeslicing_was_removed = time_now
                            enable_long_slice = False
                        else:
                            enable_long_slice = True
                        start_time_now = time.time()
                        if enable_long_slice:
                            sleep_element = element_utils.sleep_until_next_tick_element()
                        else:
                            sleep_element = elements.SleepElement(date_and_time.TimeSpan(0))
                        yield timeline.run_child(sleep_element)
                        self._request.on_end_of_time_slicing(start_time_now)
                        if self._sim is None or not self._request.valid:
                            self._clean_up()
                            raise autonomy.autonomy_exceptions.AutonomyExitException()
                        start_time = time.clock()
                        return True

            best_threshold = None
            while True:
                self._inventory_posture_score_cache = {}
                objects_to_score = self._request.objects_to_score_gen(self._actively_scored_motives)
                ts4mp_log("stuff", "Objects to score: {}".format(len(objects_to_score)))
                #to_sample = min(len(objects_to_score), 10)
                #objects_to_score = WeakSet(random.sample(objects_to_score, to_sample))
                objects_to_score = WeakSet(objects_to_score)
               # objects_to_score = WeakSet(random.sample(self._request.objects_to_score_gen(self._actively_scored_motives, 5))
                ts4mp_log("stuff", "Objects to score: {}".format(len(objects_to_score)))
                while 1:
                    yield from timeslice_if_needed_gen(timeline)
                    try:
                        obj = objects_to_score.pop()
                    except KeyError:
                        break
                    with Timer("Score Object Interactions"):
                        object_result, best_threshold = yield from self._score_object_interactions_gen(timeline, obj, timeslice_if_needed_gen, None, best_threshold)
                        if self._gsi_objects is not None:
                            self._gsi_objects.append(object_result.get_log_data())
                        if not obj.is_sim:
                            inventory_component = obj.inventory_component
                            if inventory_component and inventory_component.should_score_contained_objects_for_autonomy and inventory_component.inventory_type not in self._inventory_posture_score_cache:
                                best_threshold = yield from self._score_object_inventory_gen(timeline, inventory_component, timeslice_if_needed_gen, best_threshold)
                            else:
                                continue

                for aop_list in self._limited_affordances.values():
                    valid_aop_list = [aop_data for aop_data in aop_list if aop_data.aop.target is not None]
                    ts4mp_log("stuff", "Aops to score: {}".format(len(valid_aop_list)))

                    num_aops = len(valid_aop_list)
                    if num_aops > self.NUMBER_OF_DUPLICATE_AFFORDANCE_TAGS_TO_SCORE:
                        final_aop_list = random.sample(valid_aop_list, self.NUMBER_OF_DUPLICATE_AFFORDANCE_TAGS_TO_SCORE)
                    else:
                        final_aop_list = valid_aop_list
                        
                    with Timer("Score AOPs"):

                        for aop_data in final_aop_list:
                            interaction_result, interaction, route_time = yield from self._create_and_score_interaction(timeline, aop_data.aop, aop_data.inventory_type, best_threshold)
                            if not interaction_result:
                                if self._request.record_test_result is not None:
                                    self._request.record_test_result(aop_data.aop, '_create_and_score_interaction', interaction_result)
                                if self._gsi_interactions is not None:
                                    self._gsi_interactions.append(interaction_result)
                                continue
                            _, best_threshold = self._process_scored_interaction(aop_data.aop, interaction, interaction_result, route_time, best_threshold)

                self._limited_affordances.clear()
                if not motives_to_score:
                    break
                    
                with Timer("Statistics to Score"):

                    self._formerly_scored_motives.update(self._actively_scored_motives)
                    variance_score = self._motive_scores[motives_to_score[0]]
                    for motive in self._found_motives:
                        variance_score = max(variance_score, self._motive_scores[motive])

                    variance_score *= AutonomyMode.FULL_AUTONOMY_STATISTIC_SCORE_VARIANCE
                    self._actively_scored_motives = {stat.stat_type for stat in itertools.takewhile(lambda desire: self._motive_scores[desire] >= variance_score, motives_to_score)}
                    if not self._actively_scored_motives:
                        break
                    if self._found_valid_interaction:
                        motives_to_score = []
                    else:
                        motives_to_score = motives_to_score[len(self._actively_scored_motives):]

            final_valid_interactions = None
            for i in AutonomyInteractionPriority:
                if i not in self._valid_interactions:
                    continue
                valid_interactions = self._valid_interactions[i]
                if valid_interactions:
                    final_valid_interactions = valid_interactions
                    break

            self._request.valid_interactions = final_valid_interactions
            if self._gsi_interactions is not None:
                self._request.gsi_data = {GSIDataKeys.COMMODITIES_KEY: self._motive_scores.values(),  GSIDataKeys.AFFORDANCE_KEY: self._gsi_interactions,  GSIDataKeys.PROBABILITY_KEY: [],  GSIDataKeys.OBJECTS_KEY: self._gsi_objects, 
                 GSIDataKeys.MIXER_PROVIDER_KEY: None, 
                 GSIDataKeys.MIXERS_KEY: [],  GSIDataKeys.REQUEST_KEY: self._request.get_gsi_data()}
            #ts4mp_log("FullAutonomy", str(final_valid_interactions))
            #ts4mp_log("potential", "end")
            return final_valid_interactions    
    except Exception as e:
        ts4mp_log("FullAutonomy", str(e))
        ts4mp_log("FullAutonomy", 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

import objects.script_object 
from carry.carry_utils import get_carried_objects_gen

def potential_interactions(self, context, get_interaction_parameters=None, allow_forwarding=True, **kwargs):
    try:
        count = 0
        aops = []
        for affordance in self.super_affordances(context):
            if not self.supports_affordance(affordance):
                pass
            if get_interaction_parameters is not None:
                interaction_parameters = get_interaction_parameters(affordance, kwargs)
            else:
                interaction_parameters = kwargs
            for aop in affordance.potential_interactions(self, context, **interaction_parameters):
                count += 1
                aops.append(aop)
                yield aop
        #ts4mp_log("potential", "{} has: {} affordances: {}".format(self, count, aops))
        if allow_forwarding and self.allow_aop_forward():
            for aop in self._search_forwarded_interactions(context, get_interaction_parameters=get_interaction_parameters, **kwargs):
                yield aop
        if self.parent is not None:
            yield from self.parent.child_provided_aops_gen(self, context, **kwargs)
        club_service = services.get_club_service()
        if club_service is not None:
            for (club, affordance) in club_service.provided_clubs_and_interactions_gen(context):
                aop = AffordanceObjectPair(affordance, self, affordance, None, associated_club=club, **kwargs)
                if aop.test(context):
                    yield aop
        context_sim = context.sim
        if context_sim is not None and context_sim.posture_state is not None:
            for (_, _, carried_object) in get_carried_objects_gen(context_sim):
                yield from carried_object.get_provided_aops_gen(self, context, **kwargs)
    except Exception as e:
        ts4mp_log("potential", e)
        
        
objects.script_object.ScriptObject.potential_interactions = potential_interactions
autonomy.autonomy_service.AutonomyService._update_gen = _update_gen
autonomy.autonomy_modes.AutonomyMode.run_gen = run_gen
autonomy.autonomy_modes.FullAutonomy._run_gen = _run_gen