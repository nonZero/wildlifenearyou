﻿package com.supereveildevfort.nov2008.profilepicture {	import flash.events.ErrorEvent;			import com.supereveildevfort.nov2008.profilepicture.events.SubTabEvent;			import flash.display.Bitmap;	import flash.display.LoaderInfo;	import flash.display.MovieClip;	import flash.events.Event;	import com.gskinner.motion.GTween;	import com.niquimerret.events.InteractionEvent;	import com.supereveildevfort.nov2008.profilepicture.controllers.TabWindowController;	import com.supereveildevfort.nov2008.profilepicture.data.CurrentProfileImageData;	import com.supereveildevfort.nov2008.profilepicture.data.ImageData;	import com.supereveildevfort.nov2008.profilepicture.data.ProfileImageData;	import com.supereveildevfort.nov2008.profilepicture.events.ElementEvent;	import com.supereveildevfort.nov2008.profilepicture.ui.PictureDisplay;	import com.supereveildevfort.nov2008.profilepicture.ui.buttons.DefaultButton;	import br.com.stimuli.loading.BulkErrorEvent;	import br.com.stimuli.loading.BulkLoader;	import br.com.stimuli.loading.BulkProgressEvent;			/**	 * @class AppController.as	 * @namespace com.supereveildevfort.nov2008.profilepicture	 * @author Niqui Merret	 * @version 1.0	 * @date Nov 24, 2008	 * @description	 * @usage	 * NOTE:	 * TODO:	 *	 */	public class AppController extends MovieClip 	{		public var staticCopy : MovieClip;		public var loader : MovieClip;		private var mBulkLoader : BulkLoader;		private var mTabs : TabWindowController;		private var mPictureDisplay : PictureDisplay;		private var mSaveButton : DefaultButton;		private var mProfileXML : String;		private var mProfileImagesXML : String;		private var mProfileUpdate : String;		public function AppController ()		{						staticCopy.alpha = 0;						//load in the paths			var varsObj : Object = LoaderInfo(this.root.loaderInfo).parameters;									if (varsObj.profile_xml == null)			{				mProfileXML = "../xml/profile.xml";			}			else			{				mProfileXML = varsObj.profile_xml;			}									if (varsObj.profile_images_xml == null)			{				mProfileImagesXML = "../xml/profile-images.xml";			}			else			{				mProfileImagesXML = varsObj.profile_images_xml;			}									if (varsObj.profile_update == null)			{				mProfileUpdate = "faces/update/";			}			else			{				mProfileUpdate = varsObj.profile_update;			}						ProfileImageData.getInstance().setURL(mProfileUpdate);			ProfileImageData.getInstance().addEventListener(Event.COMPLETE, onProfileImageSaveComplete);			ProfileImageData.getInstance().addEventListener(ErrorEvent.ERROR, onProfileImageSaveError);						init();		}				private function init () : void		{						mBulkLoader = new BulkLoader("main");			mBulkLoader.add(mProfileImagesXML);			mBulkLoader.addEventListener(BulkProgressEvent.COMPLETE, onAllItemsLoaded);			mBulkLoader.addEventListener(BulkErrorEvent.ERROR, onLoadError);			mBulkLoader.start();		}		private function onAllItemsLoaded (e : BulkProgressEvent) : void		{			trace("onAllItemsLoaded");			var imageXML : XML = mBulkLoader.getXML(mProfileImagesXML);			ImageData.getInstance().parseXML(imageXML);			ImageData.getInstance().addEventListener(Event.COMPLETE, onLoadingComplete);		}		private function onLoadingComplete (e : Event) : void		{			trace("onLoadingComplete");			mPictureDisplay = new PictureDisplay();			addChild(mPictureDisplay);			mPictureDisplay.x = 10;			mPictureDisplay.y = 50;			mPictureDisplay.alpha = 0;						CurrentProfileImageData.getInstance().loadDefault(mProfileXML);			CurrentProfileImageData.getInstance().addEventListener(Event.COMPLETE, setDefault);						mTabs = new TabWindowController(ImageData.getInstance().profileImages);			addChild(mTabs);			mTabs.y = mPictureDisplay.y + mPictureDisplay.height + 20;			mTabs.x = 10;			mTabs.alpha = 0;			mTabs.addEventListener(ElementEvent.FACEPART_SELECTED, onItemSelected);			mTabs.addEventListener(SubTabEvent.SUB_TAB_ITEM_CLEARED, onItemCleared);						mSaveButton = new DefaultButton("Save");			addChild(mSaveButton);			mSaveButton.addEventListener(InteractionEvent.CLICKED, onSave);			mSaveButton.x = mPictureDisplay.width + mPictureDisplay.x - mSaveButton.width;			mSaveButton.y = mPictureDisplay.height + mPictureDisplay.y - mSaveButton.height;			mSaveButton.alpha = 0;									var picTween : GTween = new GTween(mPictureDisplay, 0.2, {alpha: 1});			var tabsTween : GTween = new GTween(mTabs, 0.2, {alpha: 1});			var saveTween : GTween = new GTween(mSaveButton, 0.2, {alpha: 1});			var staticTween : GTween = new GTween(staticCopy, 0.2, {alpha: 1});						loader.visible = false;		}				private function onItemCleared (e : SubTabEvent) : void		{			mPictureDisplay.clearCurrent(e.lable);		}		public function setDefault (e : Event) : void		{						var current : Array = CurrentProfileImageData.getInstance().structure;						for (var i : Number = 0;i < current.length; i++) 			{				current[i].image = new Bitmap();				current[i].image.bitmapData = ImageData.getInstance().getBitmapData(current[i].selectedID);			}			mPictureDisplay.setCurrent(current);			mTabs.setDefaults();		}		private function onSave (e : InteractionEvent) : void		{						ProfileImageData.getInstance().saveImage(mPictureDisplay.userImage);			mPictureDisplay.activateSaveProgress();			mSaveButton.alpha = 0.5;			mSaveButton.buttonMode = false;					}		private function onProfileImageSaveError (e : ErrorEvent) : void		{			mPictureDisplay.setSaveError();			mSaveButton.alpha = 1;			mSaveButton.buttonMode = true;					}		private function onProfileImageSaveComplete (e : Event) : void		{			mPictureDisplay.deactivateSaveProgress();			mSaveButton.alpha = 1;			mSaveButton.buttonMode = true;					}		private function onItemSelected (event : ElementEvent) : void		{			mPictureDisplay.element = event.facePart;		}		private function onLoadError (event : BulkErrorEvent) : void		{			trace(event.errors);		}	}}