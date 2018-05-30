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
    notification = UiDialogNotification.TunableFactory().default(services.get_active_sim(), text=lambda **_: LocalizationHelperTuning.get_raw_text("Autonomy time: {0:.2} s".format(time)))
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
                show_notif3( (self.t2 - self.t1) )
        ts4mp_log(self.name, "time: {}".format((self.t2 - self.t1) * 1000))

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

def run_gen(self, timeline, timeslice):

    self._motive_scores = self._score_motives()
    #ts4mp_log("Modes", str(self._motive_scores))
    generat = self._run_gen(timeline, timeslice)
    with Timer("Modes"):
        for value in generat:
            ts4mp_log("Modes", value)
    result = yield from self._run_gen(timeline, timeslice)
    return result
        
autonomy.autonomy_service.AutonomyService._update_gen = _update_gen
autonomy.autonomy_modes.AutonomyMode.run_gen = run_gen
